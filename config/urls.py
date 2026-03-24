from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from home.views import HomeView, DownloadWorkView, SubjectSpecialtyApiView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('download/<int:pk>/', DownloadWorkView.as_view(), name='download_work'),
    path('api/subject-specialty/<int:subject_id>/', SubjectSpecialtyApiView.as_view(), name='subject_specialty_api'),
    path('admin/', admin.site.urls),
]

# Служба статичних та медіа файлів в розробці
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
