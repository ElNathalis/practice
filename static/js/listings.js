// Сортировка таблицы
document.querySelectorAll('th[data-sort]').forEach(header => {
    header.addEventListener('click', () => {
        const sortKey = header.getAttribute('data-sort');
        const isAsc = header.classList.contains('sorted-asc');

        // Сброс сортировки для всех заголовков
        document.querySelectorAll('th[data-sort]').forEach(h => {
            h.classList.remove('sorted-asc', 'sorted-desc');
        });

        // Установка нового направления сортировки
        header.classList.add(isAsc ? 'sorted-desc' : 'sorted-asc');

        // Сортировка таблицы
        sortTable(sortKey, isAsc);
    });
});

function sortTable(sortKey, ascending) {
    const table = document.querySelector('#listingsTableBody');
    const rows = Array.from(table.querySelectorAll('tr')).filter(row => row.cells.length > 1);

    rows.sort((a, b) => {
        let aValue, bValue;

        switch(sortKey) {
            case 'title':
                aValue = a.cells[0].textContent.trim();
                bValue = b.cells[0].textContent.trim();
                return ascending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);

            case 'price':
                aValue = parseInt(a.cells[1].textContent.replace(/\D/g, ''));
                bValue = parseInt(b.cells[1].textContent.replace(/\D/g, ''));
                return ascending ? aValue - bValue : bValue - aValue;

            case 'city':
                aValue = a.cells[2].textContent.trim();
                bValue = b.cells[2].textContent.trim();
                return ascending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);

            case 'property_type':
                aValue = a.cells[3].textContent.trim();
                bValue = b.cells[3].textContent.trim();
                return ascending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
        }
    });

    // Очистка и перестроение таблицы
    table.innerHTML = '';
    rows.forEach(row => table.appendChild(row));
}

// Фильтрация объявлений
document.getElementById('applyFilters').addEventListener('click', applyFilters);

function applyFilters() {
    const searchText = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const cityFilter = document.getElementById('cityFilter').value;
    const propertyTypeFilter = document.getElementById('propertyTypeFilter').value;

    document.querySelectorAll('#listingsTableBody tr').forEach(row => {
        if (row.cells.length < 2) return; // Пропускаем строку с пустым состоянием

        const title = row.cells[0].textContent.toLowerCase();
        const status = row.cells[4].querySelector('.badge').textContent.trim();
        const city = row.cells[2].textContent.trim();
        const propertyType = row.cells[3].textContent.trim();

        const matchesSearch = searchText === '' || title.includes(searchText);
        const matchesStatus = statusFilter === 'all' ||
                            (statusFilter === 'active' && status === 'Активно') ||
                            (statusFilter === 'sold' && status === 'Продано') ||
                            (statusFilter === 'archived' && status === 'Архив');
        const matchesCity = cityFilter === 'all' || city === cityFilter;
        const matchesPropertyType = propertyTypeFilter === 'all' || propertyType === propertyTypeFilter;

        row.style.display = matchesSearch && matchesStatus && matchesCity && matchesPropertyType ? '' : 'none';
    });
}

// Динамическое заполнение фильтров
document.addEventListener('DOMContentLoaded', () => {
    const cities = new Set();
    const propertyTypes = new Set();

    document.querySelectorAll('#listingsTableBody tr').forEach(row => {
        if (row.cells.length > 2) {
            cities.add(row.cells[2].textContent.trim());
            if (row.cells[3]) {
                propertyTypes.add(row.cells[3].textContent.trim());
            }
        }
    });

    const cityFilter = document.getElementById('cityFilter');
    cities.forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
        cityFilter.appendChild(option);
    });

    const propertyTypeFilter = document.getElementById('propertyTypeFilter');
    propertyTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        propertyTypeFilter.appendChild(option);
    });
});