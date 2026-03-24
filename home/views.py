from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import FileResponse, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import ExtractYear
from django.contrib.auth.models import User
from .models import Work, Specialty, Subject


class HomeView(View):
    def get(self, request):
        # Отримання профілю користувача для фільтрації
        profile = None
        if request.user.is_authenticated and not request.user.is_superuser:
            profile = getattr(request.user, 'profile', None)

        # Базові запити для статистики та фільтрів
        qual_query = Work.objects.filter(work_type='qualification', approved=True)
        course_query = Work.objects.filter(work_type='course', approved=True)
        spec_query = Specialty.objects.all()
        subj_query = Subject.objects.all()
        years_query = Work.objects.filter(approved=True)

        # Обмеження для різних ролей
        if profile:
            # 1. Логіка для спеціальності (якщо є)
            if profile.specialty and (profile.role == 'viewer' or profile.role == 'qualification_editor'):
                qual_query = qual_query.filter(specialty=profile.specialty)
                course_query = course_query.filter(specialty=profile.specialty)
                spec_query = spec_query.filter(pk=profile.specialty.pk)
                years_query = years_query.filter(specialty=profile.specialty)
            
            # 2. Логіка для предметів
            has_assigned_subjects = profile.subject_id or profile.subjects.exists()
            is_course_role = (profile.role == 'course_editor' or profile.role == 'viewer' or 
                              (profile.role == 'qualification_editor' and has_assigned_subjects))
            
            if is_course_role:
                subjects_ids = list(profile.subjects.values_list('pk', flat=True))
                if profile.subject:
                    subjects_ids.append(profile.subject.pk)
                
                if subjects_ids:
                    qual_query = qual_query.filter(subject_id__in=subjects_ids)
                    course_query = course_query.filter(subject_id__in=subjects_ids)
                    subj_query = Subject.objects.filter(pk__in=subjects_ids)
                    years_query = years_query.filter(subject_id__in=subjects_ids)

        # Статистика (завжди загальна)
        qualification_count = Work.objects.filter(work_type='qualification', approved=True).count()
        course_count = Work.objects.filter(work_type='course', approved=True).count()
        specialties_count = Specialty.objects.count()

        # Дані для фільтрів (випадаючі списки)
        specialties = spec_query
        subjects = subj_query
        years = years_query.annotate(
            year=ExtractYear('defense_date')
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        # Обробка пошукового запиту
        title = request.GET.get('title')
        specialty = request.GET.get('specialty')
        work_type = request.GET.get('work_type')
        year = request.GET.get('year')
        subject = request.GET.get('subject')

        # Базовий запит для списку робіт
        works_query = Work.objects.filter(approved=True)

        if profile:
            # Початкове обмеження за спеціальністю
            if profile.specialty and (profile.role == 'viewer' or profile.role == 'qualification_editor'):
                works_query = works_query.filter(specialty=profile.specialty)
            
            # Додаткове/альтернативне обмеження за предметами
            has_assigned_subjects = profile.subject_id or profile.subjects.exists()
            is_course_role = (profile.role == 'course_editor' or profile.role == 'viewer' or 
                              (profile.role == 'qualification_editor' and has_assigned_subjects))
            
            if is_course_role:
                subjects_ids = list(profile.subjects.values_list('pk', flat=True))
                if profile.subject:
                    subjects_ids.append(profile.subject.pk)
                if subjects_ids:
                    # Якщо у користувача є і спеціальність, і предмети, вони бачать ОБИДВА (через OR)
                    from django.db.models import Q
                    if profile.specialty and (profile.role == 'qualification_editor' or profile.role == 'viewer'):
                         # Вони вже відфільтровані за спец. вище, але для гібрида це може бути OR
                         # Повертаємо works_query до базового і робимо складний фільтр
                         works_query = Work.objects.filter(approved=True).filter(
                             Q(specialty=profile.specialty) | Q(subject_id__in=subjects_ids)
                         )
                    else:
                        works_query = works_query.filter(subject_id__in=subjects_ids)

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
        
        # Перевірка прав доступу для Читача (viewer)
        if not request.user.is_superuser:
            profile = getattr(request.user, 'profile', None)
            if profile:
                has_access = False
                
                # Доступ як суперкористувач (вже перевірено) або адмін роль?
                if profile.role == 'admin':
                    has_access = True
                
                # Перевірка за спеціальністю
                if profile.specialty and work.specialty == profile.specialty:
                    if profile.role in ['viewer', 'qualification_editor']:
                        has_access = True
                
                # Перевірка за предметами
                has_assigned_subjects = profile.subject_id or profile.subjects.exists()
                is_course_role = (profile.role == 'course_editor' or profile.role == 'viewer' or 
                                  (profile.role == 'qualification_editor' and has_assigned_subjects))
                
                if is_course_role:
                    subjects_ids = list(profile.subjects.values_list('pk', flat=True))
                    if profile.subject:
                        subjects_ids.append(profile.subject.pk)
                    if work.subject and work.subject.pk in subjects_ids:
                        has_access = True
                
                # Якщо немає ніяких обмежень у viewer - він бачить все
                if profile.role == 'viewer' and not profile.specialty and not profile.subject and not profile.subjects.exists():
                    has_access = True
                
                if not has_access:
                    raise Http404("У вас немає прав для перегляду цієї роботи")

        if not work.pdf_file:
            raise Http404("Файл відсутній")
            
        # Повертаємо файл
        return FileResponse(work.pdf_file.open('rb'), as_attachment=False)

from django.http import JsonResponse
class SubjectSpecialtyApiView(View):
    """API для отримання ID спеціальності за ID предмета"""
    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, pk=subject_id)
        return JsonResponse({
            'specialty_id': subject.specialty.id if subject.specialty else None
        })
