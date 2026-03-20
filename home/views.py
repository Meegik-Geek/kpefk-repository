from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import FileResponse, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import ExtractYear
from django.contrib.auth.models import User
from .models import Work, Specialty, Subject


class HomeView(View):
    def get(self, request):
        # Статистика
        qualification_count = Work.objects.filter(work_type='qualification', approved=True).count()
        course_count = Work.objects.filter(work_type='course', approved=True).count()
        specialties_count = Specialty.objects.count()

        # Дані для фільтрів (випадаючі списки)
        specialties = Specialty.objects.all()
        subjects = Subject.objects.all()

        # Отримуємо унікальні роки захисту для фільтра
        years = Work.objects.filter(approved=True).annotate(
            year=ExtractYear('defense_date')
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        # Обробка пошукового запиту
        title = request.GET.get('title')
        specialty = request.GET.get('specialty')
        work_type = request.GET.get('work_type')
        year = request.GET.get('year')
        subject = request.GET.get('subject')

        works_query = Work.objects.filter(approved=True)
        is_search = any([title, specialty, work_type, year, subject])

        if is_search:
            from django.db.models import Q
            if title:
                works_query = works_query.filter(Q(title__icontains=title) | Q(author__icontains=title))
            if specialty:
                works_query = works_query.filter(specialty_id=specialty)
            if work_type:
                works_query = works_query.filter(work_type=work_type)
            if year:
                works_query = works_query.filter(defense_date__year=year)
            if subject:
                works_query = works_query.filter(subject_id=subject)
                
            latest_works = works_query.order_by('-uploaded_at')
            search_active = True
        else:
            # Останні затверджені роботи (наприклад, 3)
            latest_works = works_query.order_by('-uploaded_at')[:3]
            search_active = False

        context = {
            'qualification_count': qualification_count,
            'course_count': course_count,
            'specialties_count': specialties_count,
            
            'specialties': specialties,
            'subjects': subjects,
            'years': years,
            
            'latest_works': latest_works,
            'search_active': search_active,
        }
        return render(request, 'index.html', context)

class DownloadWorkView(LoginRequiredMixin, View):
    """View для завантаження PDF файлу з доступом тільки для авторизованих користувачів"""
    
    def get(self, request, pk):
        work = get_object_or_404(Work, pk=pk)
        
        if not work.pdf_file:
            raise Http404("Файл відсутній")
            
        # Повертаємо файл
        return FileResponse(work.pdf_file.open('rb'), as_attachment=False)
