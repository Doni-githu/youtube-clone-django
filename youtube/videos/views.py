from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from httpx import delete

from .models import Video, VideoVote
from .forms import VideoUploadForm
from .imagekit_client import delete_video, upload_thumbnail, upload_video

@require_POST
@login_required
def video_upload(request): # Uploading to the imagekit
    form = VideoUploadForm(request.POST, request.FILES)
    if form.is_valid():
        video_file = form.cleaned_data['video_file']
        custom_thumbnail = request.POST.get("thumbnail_data", "")

        try:
            result = upload_video(
                file_data=video_file.read(),
                file_name=video_file.name
            )

            thumbnail_url = ""
            if custom_thumbnail and custom_thumbnail.startswith("data:image"): # making a custom thumbnail for video
                try:
                    base_name = video_file.name.rsplit(".", 1)[0]
                    thumb_result = upload_thumbnail(
                        file_data=custom_thumbnail,
                        file_name=base_name + "_thumb.jpg"
                    )
                    thumbnail_url = thumb_result["url"]
                except Exception as e:
                    print(e)
                    pass

            video = Video.objects.create(
                user=request.user,
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                file_id=result["file_id"],
                video_url=result["url"],
                thumbnail_url=thumbnail_url,
            )

            return JsonResponse({
                "success": True,
                "video_id": video.pk, # type: ignore
                "message": "Video uploaded successfully"
            })
        
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    errors = []
    for field, field_errors in form.errors.items(): # Checking if the any exception
        for error in field_errors:
            errors.append(f"{field}: {error}" if field != "__all__" else error)
    return JsonResponse({"success": False, "errors": ";".join(errors)})


@login_required
def video_upload_page(request):
    return render(request, "videos/upload.html", {"form": VideoUploadForm()}) 



def video_list(request): # for home page 
    videos = Video.objects.all()
    return render(request, 'videos/home.html', {"videos": videos})  

def video_detail(request, video_id): # giving the detail
    video = get_object_or_404(Video.objects, id=video_id)
    
    video.views +=1
    video.save(update_fields=["views"])

    user_vote = None
    if request.user.is_authenticated:
        vote = VideoVote.objects.filter(user=request.user, video=video).first()
        if vote:
            user_vote = vote.value
    return render(request, "videos/detail.html", {"video": video, "user_vote": user_vote})

def channel_videos(request, username):
    videos = Video.objects.filter(user__username=username)
    return render(request, "videos/channel.html", {"videos": videos, "channel_name": username})

@login_required
@require_POST # request require POST and It for delete a video if the user own the video
def delete_video_view(request, video_id):
    video = get_object_or_404(Video, id=video_id, user=request.user) # Automatically raise Exection so i don't need to do anything
    
    try:
        delete_video(video.file_id) # main login for deleting image from imagekit in this
    except Exception as e:
        print(e)
        pass

    video.delete()
    return JsonResponse({"success": True, "message": "video deleted"})

@login_required # type: ignore
@require_POST
def video_vote(request, video_id):
    video = get_object_or_404(Video.objects, id=video_id)
    vote_type = request.POST.get("vote")

    if vote_type not in ["like", 'dislike']:
        return JsonResponse({"success": False, "error": "Invalid vote"}, status=400)
    
    value = VideoVote.LIKE if vote_type == "like" else VideoVote.DISLIKE
    existing_vote = VideoVote.objects.filter(user=request.user, video=video).first()


    if existing_vote: # if exist so I wil just change or delete existing
        if existing_vote.value == value:
            if value == VideoVote.LIKE:
                video.likes -=1
            else:
                video.dislikes -=1
            existing_vote.delete()
            user_vote = None
        else:
            if value == VideoVote.LIKE:
                video.likes +=1
                video.dislikes -=1
            else:
                video.likes -=1
                video.dislikes +=1
            existing_vote.value = value
            existing_vote.save()
            user_vote = value
    else: # if it is not, I just add one vote for user and apply video
        VideoVote.objects.create(user=request.user, video=video, value=value)
        if value == VideoVote.LIKE:
            video.likes +=1
        else:
            video.dislikes +=1
        user_vote = value
    
    video.save(update_fields=["likes", "dislikes"])

    return JsonResponse({
        "likes": video.likes,
        "dislikes": video.dislikes,
        "user_vote": user_vote
    })