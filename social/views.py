from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.models import User, auth
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from social.models import Profile, Post, PostImage, PostComment, Message, Notification
from django.db.models import Q
from django.core.paginator import Paginator
import time

# Create your views here.
def index(request):
    if request.user.is_authenticated:
        messages.info(request, f'{request.user.username} welcome')
        return redirect(request.GET.get('next','home'))
    if request.method =='POST':
        user_check = request.POST.get('user_check')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.get(email=user_check)
            username = user_obj.username
        except User.DoesNotExist:
            username=user_check
        user =authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            request.session.set_expiry(None)
            messages.info(request, f"Welcome back {user.username}")
            return redirect(request.GET.get('next', 'home'))
        else:
            messages.info(request,'Invalid Login details')
            return redirect('/')
    return render(request, 'index.html')


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('pass1')
        password2 = request.POST.get('pass2')
        if (len(username) < 5):
            messages.info(request, 'Username must contain atleast 5 Characters')
            return redirect('register')
        elif User.objects.filter(username=username):
            messages.info(request, ' Username is taken Already')
            return redirect('register')
        elif User.objects.filter(email=email):
            messages.info(request, 'Email is taken Already')
            return redirect('register')
        elif (password != password2):
            messages.info(request, 'Password are not the Same')
            return redirect('register')
        else:
            user=User.objects.create_user(username=username, email=email, password=password)
            Profile.objects.create(user=user)
            messages.info(request, f'Welcome {username}, You can now Login')
            return redirect('/')


    return render(request, 'register.html')
@login_required(login_url='/')
def home(request):
    page_number = request.GET.get('page', 1)
    post_list = Post.objects.all().order_by('?')
    paginator = Paginator(post_list, 5)
    try:
        page_obj = paginator.page(page_number)
    except Exception:
        page_obj = paginator.page(paginator.num_pages)

    if request.headers.get('HX-Request'):
        time.sleep(2)
        return render(request, 'snippet/scrolling.html', {'page_obj':page_obj})
    
    members = User.objects.all().order_by('?')
    return render(request, 'home.html', {'page_obj':page_obj, 'members': members})


    
def post(request):
    if request.method =='POST':
        content = request.POST.get('content','').strip()
        images = request.FILES.getlist('images')
        if not content and not images:
            return redirect(request.META.get('HTTP_REFERER'))
        post=Post.objects.create(author=request.user, content=content)
        if images:
            for image in images:
                PostImage.objects.create(post=post, image=image)
        return redirect('home')
    

    return render(request, 'post.html')

        
@login_required(login_url='/')
def like_post(request, post_id):
    post = get_object_or_404(Post, post_id=post_id)
    if request.user not in post.likes.all():
        post.likes.add(request.user)
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author,
                actor = request.user,
                post=post,
                message=f' Liked your post {post.content}')
    else:
        post.likes.remove(request.user)
    return render(request, 'snippet/post_like.html', {'post':post, 'post_id':post_id})  
       



@login_required(login_url='/')
def post_comment(request, post_id):
    post=get_object_or_404(Post, post_id=post_id)
    
    comments=PostComment.objects.filter(post=post).order_by('-created_at')
    return render(request, 'postcomment.html', {'post':post, 'comments': comments})
@login_required(login_url='/')
def postcomment(request, post_id):
    post=get_object_or_404(Post, post_id=post_id)
    if request.method == 'POST':
        comment = request.POST.get('comment')
        comment=PostComment.objects.create(post=post, author=request.user, comment=comment)
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author,
                actor = request.user,
                 message=f"  commented on your post {post.content}",
                 post=post)
        return render(request, 'snippet/comment_list.html', {'post':post, 'comment': comment})
    

def comment_like(request, comment_id):
    comment=get_object_or_404(PostComment, comment_id=comment_id)
    if request.user in comment.like.all():
        comment.like.remove(request.user)
    else:
        comment.like.add(request.user)
    return render(request, 'snippet/comment_like.html', {'comment':comment, 'comment_id':comment_id})


@login_required(login_url='/')
def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user)
    profile = Profile.objects.get(user=user)
    following =profile.followings.count()

    context={
        'user':user,
        'posts':posts,
        'profile':profile,
        'following': following
    }
    
    return render(request, 'profile.html', context)


@login_required(login_url='/')
def update_profile(request, username):
    user = request.user
    profile= request.user.profile
    if request.method =='POST':
        fname= request.POST.get('fname')
        lname = request.POST.get('lname')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        location = request.POST.get('location')
        image = request.FILES.get('image')
        bio = request.POST.get('bio')
        if fname and lname:
            user.first_name=fname
            user.last_name=lname
            user.save()
        if phone and address and location and bio:
            profile.phone = phone
            profile.address= address
            profile.location = location
            profile.bio = bio
            profile.save()
        if image:
            profile.picture = image
            profile.save()
        messages.info(request, 'Profile Updated Successfully')
        return redirect('profile', username=request.user.username)


    return render(request, 'update_profile.html', {'profile':profile})

def follow(request, username):
    user = get_object_or_404(User, username=username)
    profile= Profile.objects.get(user=user)
    if request.user not in profile.followers.all():
        profile.followers.add(request.user)
        profile.followings.add(user)
        messages.info(request, 'Following')
        return redirect(request.META.get('HTTP_REFERER'))
    else:
        profile.followers.remove(request.user)
        profile.followings.remove(user)
        messages.info(request, 'unFollowing')
        return redirect(request.META.get('HTTP_REFERER'))
@login_required(login_url='/')
def search(request):
    quary = request.GET.get('q')
    if quary:
        users = User.objects.filter(
            Q(username__icontains=quary) | Q(email__icontains=quary) | Q(first_name__icontains=quary) | Q(last_name__icontains=quary)
        )
        return render(request, 'search.html', {'quary': quary, 'users':users})
    return render(request, 'search.html')

@login_required(login_url='/')
def message(request, username):
    receiver = get_object_or_404(User, username=username)
    sender = request.user
    unread_message = Message.objects.filter(
        receiver=sender, sender=receiver, is_read=False
    )
    for msg in unread_message:
        msg.is_read = True
        msg.save()
    if request.method =='POST':
        conversation = request.POST.get('conversation')
        if message:
            Message.objects.create(sender=sender, receiver= receiver, conversation=conversation)
            messages.info(request, 'Message Sent')
            return redirect(request.META.get('HTTP_REFERER'))
        else:
            messages.info(request, 'You can not send empty Message')
            return redirect(request.META.get('HTTP_REFERER'))
    conversations = Message.objects.filter(
        Q(sender=sender) & Q(receiver=receiver) | Q(sender=receiver) & Q(receiver=sender)
    ).order_by('-created_at')
    return render(request, 'message.html', {'conversations':conversations})

@login_required(login_url='/')
def open_notification(request, pk):
    notifications =get_object_or_404(Notification, pk=pk, recipient=request.user)
    notifications.is_read=True
    notifications.save()
    if notifications.post: 
        return redirect('post_comment', post_id=notifications.post.post_id)
   
    return render(request, 'home.html')
    
login_required(login_url='/')
def inbox(request):
    inbox_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-created_at')
    conversations={}
    for message in inbox_messages:
        other_user=message.sender if message.sender != request.user else message.receiver
        conversations.setdefault(other_user, message)
    return render(request, 'inbox.html', {'messages':conversations.values(),})

login_required(login_url='/')
def notification_list(request):
    return render(request, 'notification.html')

def error_404(request, exception):
    return render(request, '404.html', status=404)
def logout(request):
    auth.logout(request)
    messages.info(request, 'Logout Successfully')
    return redirect('/')