from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Specialty(models.Model):
    """Спеціальність"""
    name = models.CharField(
        max_length=255,
        verbose_name="Назва спеціальності",
        unique=True
    )
    code = models.CharField(
        max_length=50,
        verbose_name="Код спеціальності",
        unique=True
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Опис"
    )

    class Meta:
        verbose_name = "Спеціальність"
        verbose_name_plural = "Спеціальності"
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Subject(models.Model):
    """Предмет (для курсових робіт)"""
    name = models.CharField(
        max_length=255,
        verbose_name="Назва предмету",
        unique=True
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name="Спеціальність",
        null=True,
        blank=True
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Опис"
    )

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предмети"
        ordering = ['name']

    def __str__(self):
        return self.name


class Work(models.Model):
    """Базова модель для кваліфікаційних та курсових робіт"""
    WORK_TYPE_CHOICES = (
        ('qualification', 'Кваліфікаційна робота (дипломний проєкт)'),
        ('course', 'Курсова робота (проєкт)'),
    )

    title = models.CharField(
        max_length=500,
        verbose_name="Назва роботи"
    )
    work_type = models.CharField(
        max_length=20,
        choices=WORK_TYPE_CHOICES,
        verbose_name="Тип роботи"
    )
    author = models.CharField(
        max_length=255,
        verbose_name="Виконавець (студент)"
    )
    supervisor = models.CharField(
        max_length=255,
        verbose_name="Науковий керівник"
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,
        verbose_name="Спеціальність"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Предмет (для курсових)"
    )
    academic_year = models.CharField(
        max_length=10,
        verbose_name="Навчальний рік",
        help_text="Формат: 2024-2025"
    )
    defense_date = models.DateField(
        verbose_name="Дата захисту/подання"
    )
    pdf_file = models.FileField(
        upload_to='works/%Y/%m/',
        verbose_name="PDF файл роботи"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата завантаження"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата оновлення"
    )
    approved = models.BooleanField(
        default=False,
        verbose_name="Схвалено модератором"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Коротка анотація"
    )

    class Meta:
        verbose_name = "Робота"
        verbose_name_plural = "Роботи"
        ordering = ['-defense_date']
        indexes = [
            models.Index(fields=['-defense_date']),
            models.Index(fields=['work_type']),
            models.Index(fields=['specialty']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_work_type_display()})"



class WorkDeletion(models.Model):
    """Реєстр видалених робіт"""
    work_title = models.CharField(
        max_length=500,
        verbose_name="Назва роботи (архів)"
    )
    author_name = models.CharField(
        max_length=255,
        verbose_name="ПІБ виконавця (архів)"
    )
    deletion_date = models.DateField(
        auto_now_add=True,
        verbose_name="Дата видалення"
    )
    reason = models.TextField(
        verbose_name="Причина видалення"
    )
    deletion_act = models.FileField(
        upload_to='deletion_acts/',
        verbose_name="Акт про вилучення",
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Видалена робота"
        verbose_name_plural = "Видалені роботи"
        ordering = ['-deletion_date']

    def __str__(self):
        return f"{self.work_title} (видалено {self.deletion_date})"


class UserProfile(models.Model):
    """Профіль користувача з роллю"""
    ROLE_CHOICES = (
        ('admin', 'Адміністратор'),
        ('qualification_editor', 'Редактор кваліфікаційних робіт'),
        ('course_editor', 'Редактор курсових робіт'),
        ('viewer', 'Читач (перегляд PDF)'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="Користувач"
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name="Роль"
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Спеціальність",
        help_text="Заповнюється для редактора кваліфікаційних робіт або для обмеження Читача конкретною спеціальністю"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Предмет (основний)",
        help_text="Заповнюється для редактора курсових робіт (як основний)"
    )
    subjects = models.ManyToManyField(
        Subject,
        blank=True,
        related_name='editor_profiles',
        verbose_name="Дозволені предмети",
        help_text="Для редактора курсових робіт або Читача: виберіть усі предмети, до яких дозволено доступ"
    )
    also_course_editor = models.BooleanField(
        default=False,
        verbose_name="Також є редактором курсових робіт",
        help_text="Якщо увімкнено, користувач (наприклад, Редактор КР) зможе також редагувати курсові роботи за вибраними предметами"
    )

    class Meta:
        verbose_name = "Профіль користувача"
        verbose_name_plural = "Профілі користувачів"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Оновлюємо права доступу користувача безпечно (без виклику пост-сейв)
        user = self.user
        changed = False
        
        if self.role == 'admin' and (not user.is_staff or not user.is_superuser):
            user.is_staff = True
            user.is_superuser = True
            changed = True
        elif self.role in ['qualification_editor', 'course_editor', 'viewer'] and (not user.is_staff or user.is_superuser):
            user.is_staff = True
            user.is_superuser = False
            changed = True
            
        if changed:
            User.objects.filter(pk=user.pk).update(is_staff=user.is_staff, is_superuser=user.is_superuser)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Автоматично створює профіль при створенні нового користувача"""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Зберегти існуючий профіль (якщо він є)
        if hasattr(instance, 'profile'):
            instance.profile.save()
