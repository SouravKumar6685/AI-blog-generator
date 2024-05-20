import json
import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from pytube import YouTube
import assemblyai as aai
import openai
from .models import BlogPost

@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data.get('link')

            if not yt_link:
                return JsonResponse({'error': 'No YouTube link provided'}, status=400)

            # Get YouTube title
            title = yt_title(yt_link)

            # Get transcription
            transcription = get_transcription(yt_link)
            if not transcription:
                return JsonResponse({'error': 'Failed to get transcript'}, status=500)

            # Generate blog content
            blog_content = generate_blog_from_transcription(transcription)
            if not blog_content:
                return JsonResponse({'error': 'Failed to generate blog article.'}, status=500)

            # Save blog in DB
            new_blog_article = BlogPost.objects.create(
                user=request.user,
                youtube_title=title,
                youtube_link=yt_link,
                generated_content=blog_content,
            )
            new_blog_article.save()

            # Return blog article as a response
            return JsonResponse({'content': blog_content})

        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    yt = YouTube(link)
    return yt.title

def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = "8ebbcbae24664e6eab3d667dc530f7ee"

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    return transcript['text'] if transcript else None

def generate_blog_from_transcription(transcription):
    openai.api_key = 'sk-proj-9Cpi4Pv931LnO0BwNLHHT3BlbkFJmuyDSWQVm69X2fqwmqdW'

    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article. Write it based on the transcript, but don't make it look like a YouTube video. Make it look like a professional blog article: \n\n{transcription}\n\nArticle:"

    response = openai.Completion.create(
        model='text-davinci-003',
        prompt=prompt,
        max_tokens=1000
    )

    return response.choices[0].text.strip() if response.choices else None

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatpassword = request.POST['repeatpassword']
        
        if password == repeatpassword:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
            else:
                user = User.objects.create_user(username, email, password)
                user.save()
                auth_login(request, user)
                return redirect('/')  # redirect to the home page
        else:
            messages.error(request, 'Passwords do not match')
    return render(request, 'signup.html')

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, 'all-block.html', {'blog_articles': blog_articles})


def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail:
        return render(request, 'blog-details.html', {'blog_details':blog_article_detail})
    else:
        return redirect('/')
    
def user_logout(request):
    auth_logout(request)
    return redirect('/')
