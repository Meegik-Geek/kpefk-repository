from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from django.db.models import Count
from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from .models import Specialty, Subject, Work, WorkDeletion, UserProfile

class EmailOrUsernameAuthenticationForm(AdminAuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Email або Ім'я користувача (Логін)"

admin.site.login_form = EmailOrUsernameAuthenticationForm

class EmailRequiredUserCreationForm(UserCreationForm):
    """Форма створення користувача з обов'язковим унікальним email"""
    email = forms.EmailField(
        required=True,
        label="Email (логін)",
        help_text="Email використовується для входу в систему"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'username', 'first_name', 'last_name')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Користувач з таким email вже існує.")
        return email.lower()


class EmailRequiredUserChangeForm(UserChangeForm):
    """Форма редагування користувача з обов'язковим унікальним email"""
    email = forms.EmailField(
        required=True,
        label="Email (логін)",
        help_text="Email використовується для входу в систему"
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Користувач з таким email вже існує.")
        return email.lower()



# Кастомізація заголовків адмін-сайту
admin.site.site_header = "Адміністрування Електронного Репозиторію"
admin.site.site_title = "Репозиторій КПЕФК"
admin.site.index_title = "Статистика та управління"


# Модифікуємо стандартний index
original_index = admin.site.index

def custom_index(request, extra_context=None):
    # Статистика робіт
    total_works = Work.objects.count()
    approved_works = Work.objects.filter(approved=True).count()
    pending_works = Work.objects.filter(approved=False).count()
    with_files = Work.objects.exclude(pdf_file='').count()
    
    # Диференціація за типом
    qualification_works = Work.objects.filter(work_type='qualification').count()
    course_works = Work.objects.filter(work_type='course').count()
    
    # За спеціальностями
    specialties_count = Specialty.objects.count()
    top_specialties = Specialty.objects.annotate(
        work_count=Count('work')
    ).order_by('-work_count')[:5]
    
    # Користувачі
    authors_count = Work.objects.values('author').distinct().count()
    supervisors_count = Work.objects.values('supervisor').distinct().count()
    
    # Архіви
    deleted_works = WorkDeletion.objects.count()
    
    extra_context = extra_context or {}
    extra_context.update({
        'total_works': total_works,
        'approved_works': approved_works,
        'pending_works': pending_works,
        'with_files': with_files,
        'qualification_works': qualification_works,
        'course_works': course_works,
        'specialties_count': specialties_count,
        'top_specialties': top_specialties,
        'authors_count': authors_count,
        'supervisors_count': supervisors_count,
        'deleted_works': deleted_works,
    })
    
    return original_index(request, extra_context)

admin.site.index = custom_index


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'work_count')
    list_filter = ('name',)
    search_fields = ('name', 'code')
    ordering = ('code',)
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'code')
        }),
        ('Додатково', {
            'fields': ('description',)
        }),
    )
    
    def work_count(self, obj):
        count = obj.work_set.count()
        return format_html(
            '<span style="background-color: #79aec8; color: white; padding: 3px 8px; border-radius: 3px;">{} робіт</span>',
            count
        )
    work_count.short_description = 'Кількість робіт'



@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'work_type_badge', 'specialty', 'defense_date', 'approved_badge', 'file_status')
    list_filter = ('work_type', 'specialty', 'approved', 'defense_date', 'uploaded_at')
    search_fields = ('title', 'author', 'supervisor')
    readonly_fields = ('uploaded_at', 'updated_at', 'file_preview', 'file_status')
    date_hierarchy = 'defense_date'
    ordering = ('-defense_date',)
    actions = ['approve_works', 'reject_works']
    
    # 1. Запит для відображення робіт в адмінці
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
            
        profile = getattr(request.user, 'profile', None)
        if profile:
            if profile.role == 'qualification_editor' and profile.specialty:
                return qs.filter(work_type='qualification', specialty=profile.specialty)
            elif profile.role == 'course_editor' and profile.subject:
                return qs.filter(work_type='course', subject=profile.subject)
                
        return qs.none()

    # 2. Обмеження форми залежно від ролі
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            profile = getattr(request.user, 'profile', None)
            if profile:
                if profile.role == 'qualification_editor':
                    # Дозволяємо тільки кваліфікаційні
                    form.base_fields['work_type'].choices = [('qualification', 'Кваліфікаційна робота (дипломний проєкт)')]
                    form.base_fields['work_type'].initial = 'qualification'
                    
                    if profile.specialty:
                        form.base_fields['specialty'].queryset = Specialty.objects.filter(id=profile.specialty.id)
                        form.base_fields['specialty'].initial = profile.specialty
                        form.base_fields['specialty'].empty_label = None # Обов'язково вибрати свою спец.
                        
                elif profile.role == 'course_editor':
                    # Дозволяємо тільки курсові
                    form.base_fields['work_type'].choices = [('course', 'Курсова робота (проєкт)')]
                    form.base_fields['work_type'].initial = 'course'
                    
                    if profile.subject:
                        form.base_fields['subject'].queryset = Subject.objects.filter(id=profile.subject.id)
                        form.base_fields['subject'].initial = profile.subject
                        form.base_fields['subject'].empty_label = None # Обов'язково вибрати свій предмет
        return form

    # 3. Перевизначення дозволів, щоб редактори могли бачити та редагувати модуль
    def has_module_permission(self, request):
        if super().has_module_permission(request): return True
        profile = getattr(request.user, 'profile', None)
        return profile and profile.role in ['qualification_editor', 'course_editor']

    def has_add_permission(self, request):
        if request.user.is_superuser: return True
        profile = getattr(request.user, 'profile', None)
        return profile and profile.role in ['qualification_editor', 'course_editor']

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        profile = getattr(request.user, 'profile', None)
        return profile and profile.role in ['qualification_editor', 'course_editor']
        
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        profile = getattr(request.user, 'profile', None)
        return profile and profile.role in ['qualification_editor', 'course_editor']

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        profile = getattr(request.user, 'profile', None)
        return profile and profile.role in ['qualification_editor', 'course_editor']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('title', 'work_type', 'specialty', 'subject', 'description')
        }),
        ('Автори та керівництво', {
            'fields': ('author', 'supervisor')
        }),
        ('Дати та академічний рік', {
            'fields': ('academic_year', 'defense_date')
        }),
        ('PDF файл', {
            'fields': ('pdf_file', 'file_preview', 'file_status')
        }),
        ('Статус', {
            'fields': ('approved',)
        }),
        ('Системні дані', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def work_type_badge(self, obj):
        colors = {
            'qualification': '#417690',
            'course': '#79aec8',
        }
        color = colors.get(obj.work_type, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_work_type_display()
        )
    work_type_badge.short_description = 'Тип роботи'
    
    def approved_badge(self, obj):
        if obj.approved:
            return format_html(
                '<span style="background-color: #417690; color: white; padding: 3px 10px; border-radius: 3px;">✓ Схвалено</span>'
            )
        return format_html(
            '<span style="background-color: #e8e8e8; color: #666; padding: 3px 10px; border-radius: 3px;">На розгляді</span>'
        )
    approved_badge.short_description = 'Статус затвердження'
    
    def file_status(self, obj):
        if obj.pdf_file:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Завантажено</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Відсутній</span>'
        )
    file_status.short_description = 'Статус файлу'
    
    def file_preview(self, obj):
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank" style="color: #417690; text-decoration: underline;">Переглянути файл</a>',
                obj.pdf_file.url
            )
        return "Файл не завантажено"
    file_preview.short_description = 'Попередній перегляд'
    
    def approve_works(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f'{updated} робіт схвалено.')
    approve_works.short_description = 'Схвалити вибрані роботи'
    
    def reject_works(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f'{updated} робіт відхилено.')
    reject_works.short_description = 'Відхилити вибрані роботи'



class WorkDeletionAdmin(admin.ModelAdmin):
    list_display = ('work_title', 'author_name', 'deletion_date', 'deletion_act_link')
    list_filter = ('deletion_date',)
    search_fields = ('work_title', 'author_name')
    readonly_fields = ('deletion_date',)
    ordering = ('-deletion_date',)
    
    fieldsets = (
        ('Видалена робота (архів)', {
            'fields': ('work_title', 'author_name', 'deletion_date')
        }),
        ('Документація', {
            'fields': ('reason', 'deletion_act')
        }),
    )
    
    def deletion_act_link(self, obj):
        if obj.deletion_act:
            return format_html(
                '<a href="{}" target="_blank">Переглянути акт</a>',
                obj.deletion_act.url
            )
        return "Немає"
    deletion_act_link.short_description = 'Акт про вилучення'


# --- Subject ---
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'course_work_count')
    search_fields = ('name',)
    ordering = ('name',)

    fieldsets = (
        ('Форма предмету', {
            'fields': ('name', 'description')
        }),
    )

    def course_work_count(self, obj):
        count = UserProfile.objects.filter(subject=obj).count()
        return format_html(
            '<span style="background-color: #79aec8; color: white; padding: 3px 8px; border-radius: 3px;">{} користувачів</span>',
            count
        )
    course_work_count.short_description = 'Редакторів'


# --- UserProfile inline (for the User admin page) ---
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'Профіль користувача'
    verbose_name_plural = 'Профіль користувача'
    fields = ('role', 'specialty', 'subject')
    extra = 0


# --- Override default UserAdmin to inject profile inline ---
class UserAdmin(BaseUserAdmin):
    form = EmailRequiredUserChangeForm
    add_form = EmailRequiredUserCreationForm
    inlines = (UserProfileInline,)

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

    add_fieldsets = (
        ('Створення користувача', {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    fieldsets = (
        ('Основні дані', {'fields': ('email', 'username', 'password')}),
        ('Персональна інформація', {'fields': ('first_name', 'last_name')}),
        ('Дозволи', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Дати', {'fields': ('last_login', 'date_joined')}),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- Standalone UserProfile admin ---
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_username', 'user_full_name', 'role_badge', 'specialty', 'subject')
    list_filter = ('role', 'specialty', 'subject')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    ordering = ('user__username',)

    fieldsets = (
        ('Користувач', {
            'fields': ('user',)
        }),
        ('Роль та доступ', {
            'fields': ('role', 'specialty', 'subject')
        }),
    )

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Логін'

    def user_full_name(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name or '—'
    user_full_name.short_description = "ПІБ"

    def role_badge(self, obj):
        colors = {
            'admin': '#c0392b',
            'qualification_editor': '#417690',
            'course_editor': '#27ae60',
            'viewer': '#7f8c8d',
        }
        color = colors.get(obj.role, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Роль'
