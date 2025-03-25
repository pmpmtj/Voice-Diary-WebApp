# Audio Recording Feature Migration Guide

## Prerequisites
- Existing Django project
- Basic understanding of Django templates and views
- Modern web browser with microphone access

## Step 1: Add Media Settings
Add these settings to your project's `settings.py`:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## Step 2: Update Main URLs
In your project's main `urls.py`, add:
```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... your existing URL patterns ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## Step 3: Create Template
Create `templates/record.html` in your project:
```html
{% extends 'base.html' %}

{% block title %}Record Audio{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h3 class="text-center">Audio Recorder</h3>
                </div>
                <div class="card-body">
                    <div class="text-center mb-4">
                        <button id="recordButton" class="btn btn-primary">
                            <i class="fas fa-microphone"></i> Start Recording
                        </button>
                        <button id="stopButton" class="btn btn-danger" disabled>
                            <i class="fas fa-stop"></i> Stop Recording
                        </button>
                    </div>
                    <div class="alert alert-info" id="statusMessage">
                        Click 'Start Recording' to begin
                    </div>
                    <div class="progress mb-3" style="display: none;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" 
                             style="width: 0%">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

{% block extra_js %}
<script>
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    const recordButton = document.getElementById('recordButton');
    const stopButton = document.getElementById('stopButton');
    const statusMessage = document.getElementById('statusMessage');
    const progressBar = document.querySelector('.progress');
    const progressBarInner = document.querySelector('.progress-bar');

    async function uploadAudio(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'local_recording.wav');

        try {
            statusMessage.textContent = 'Uploading audio file...';
            const response = await fetch('/process-audio/', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                statusMessage.textContent = 'Audio uploaded and processed successfully!';
                statusMessage.className = 'alert alert-success';
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            statusMessage.textContent = `Error: ${error.message}`;
            statusMessage.className = 'alert alert-danger';
            console.error('Upload error:', error);
        }
    }

    async function setupRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                
                // Upload to server
                await uploadAudio(audioBlob);
                
                // Also provide local download
                const audioUrl = URL.createObjectURL(audioBlob);
                const downloadLink = document.createElement('a');
                downloadLink.href = audioUrl;
                downloadLink.download = 'local_recording.wav';
                downloadLink.click();
                
                // Cleanup
                URL.revokeObjectURL(audioUrl);
                audioChunks = [];
                recordButton.disabled = false;
                stopButton.disabled = true;
                progressBar.style.display = 'none';
            };

            // Update progress bar
            mediaRecorder.onstart = () => {
                let progress = 0;
                const interval = setInterval(() => {
                    progress += 1;
                    progressBarInner.style.width = `${progress}%`;
                    if (progress >= 100) {
                        clearInterval(interval);
                    }
                }, 100);
            };

        } catch (error) {
            statusMessage.textContent = `Error: ${error.message}`;
            statusMessage.className = 'alert alert-danger';
            console.error('Error accessing microphone:', error);
        }
    }

    recordButton.addEventListener('click', async () => {
        if (!mediaRecorder) {
            await setupRecording();
        }
        
        isRecording = true;
        audioChunks = [];
        mediaRecorder.start();
        recordButton.disabled = true;
        stopButton.disabled = false;
        statusMessage.textContent = 'Recording in progress...';
        statusMessage.className = 'alert alert-info';
        progressBar.style.display = 'block';
        progressBarInner.style.width = '0%';
    });

    stopButton.addEventListener('click', () => {
        isRecording = false;
        mediaRecorder.stop();
    });
</script>
{% endblock %}
{% endblock %}
```

## Step 4: Add Views
In your app's `views.py`, add:
```python
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import os

def record(request):
    """View for the audio recording page."""
    return render(request, 'record.html')

@csrf_exempt  # Only for development. In production, handle CSRF properly
@require_http_methods(["POST"])
def process_audio(request):
    """Handle the uploaded audio file and process it."""
    try:
        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No audio file provided'}, status=400)
        
        audio_file = request.FILES['audio']
        
        # Create a directory for storing uploads if it doesn't exist
        upload_dir = os.path.join('media', 'audio_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file as incoming_recording.wav
        file_path = os.path.join(upload_dir, 'incoming_recording.wav')
        with open(file_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
        
        return JsonResponse({
            'message': 'Audio file received and processed successfully',
            'file_path': file_path
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

## Step 5: Add URLs
In your app's `urls.py`, add:
```python
from django.urls import path
from . import views

urlpatterns = [
    # ... your existing URL patterns ...
    path('record/', views.record, name='record'),
    path('process-audio/', views.process_audio, name='process_audio'),
]
```

## Step 6: Add Navigation (Optional)
Add a link to the recording page in your navigation menu or wherever appropriate:
```html
<a href="{% url 'record' %}" class="nav-link">Record Audio</a>
```

## Step 7: Test the Feature
1. Run your Django server
2. Navigate to `/record/` (or your configured URL)
3. Click "Start Recording" and grant microphone permissions
4. Record your message
5. Click "Stop Recording"
6. The file will:
   - Download locally as 'local_recording.wav'
   - Upload to server as 'incoming_recording.wav' in `media/audio_uploads/`

## Important Notes
- The feature requires HTTPS in production for microphone access
- Make sure your server has write permissions for the media directory
- Consider adding CSRF protection in production
- The audio file is saved as WAV format
- Each new recording overwrites the previous 'incoming_recording.wav'

## Customization Options
1. Change file name: Modify the `file_path` in `process_audio` view
2. Add unique filenames: Add timestamp or UUID to filename
3. Change audio format: Modify the Blob type in the JavaScript code
4. Add processing: Add your logic in the `process_audio` view

## Security Considerations
1. CSRF Protection:
   - The endpoint currently has `@csrf_exempt` for development
   - In production, remove `@csrf_exempt` and implement proper CSRF protection
   - Add authentication if needed for restricted access

2. Server Configuration:
   - Ensure server firewall/security settings allow POST requests to `/process-audio/`
   - Verify server has write permissions for `media/audio_uploads/` directory
   - Consider implementing rate limiting to prevent abuse

3. File Upload Security:
   - Validate file types and sizes
   - Consider implementing virus scanning for uploaded files
   - Set appropriate file permissions on uploaded files

4. HTTPS Requirements:
   - Microphone access requires HTTPS in production
   - Ensure all communication is encrypted
   - Use secure WebSocket connections if implementing real-time features 
