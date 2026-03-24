/**
 * JavaScript для синхронізації Спеціальності з обраним Предметом
 * в адмін-панелі при додаванні/редагуванні роботи.
 */
document.addEventListener('DOMContentLoaded', function() {
    const subjectSelect = document.getElementById('id_subject');
    const specialtySelect = document.getElementById('id_specialty');
    const workTypeSelect = document.getElementById('id_work_type');

    if (!subjectSelect || !specialtySelect) return;

    // Словник предмет -> спеціальність (передаємо через data-атрибути або Fetch)
    // Оскільки ми хочемо "WOW" ефект без перезавантаження, зробимо Fetch
    
    subjectSelect.addEventListener('change', function() {
        const subjectId = this.value;
        if (!subjectId) return;

        // Викликаємо API або використовуємо заздалегідь підготовлений маппінг
        // Для швидкості та простоти, просто знайдемо спеціальність через невеликий API endpoint
        fetch(`/api/subject-specialty/${subjectId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.specialty_id) {
                    specialtySelect.value = data.specialty_id;
                    // Підсвітимо зміну
                    specialtySelect.style.transition = 'background-color 0.5s';
                    specialtySelect.style.backgroundColor = '#e8f5e9';
                    setTimeout(() => {
                        specialtySelect.style.backgroundColor = '';
                    }, 1000);
                }
            })
            .catch(error => console.error('Error fetching subject specialty:', error));
    });
});
