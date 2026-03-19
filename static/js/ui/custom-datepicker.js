/**
 * Custom Date Picker with Day → Month → Year view switching
 * Click header to cycle through views
 */

class CustomDatePicker {
  constructor(inputElement, options = {}) {
    this.input = inputElement;
    this.options = {
      maxDate: options.maxDate || null,
      minDate: options.minDate || null,
      dateFormat: options.dateFormat || 'Y-m-d',
      ...options
    };

    this.currentView = 'day'; // 'day', 'month', 'year'
    this.selectedDate = this.parseInputDate() || new Date();
    this.viewDate = new Date(this.selectedDate);

    this.init();
  }

  parseInputDate() {
    if (this.input.value) {
      const date = new Date(this.input.value);
      return isNaN(date) ? null : date;
    }
    return null;
  }

  init() {
    // Create picker container
    this.picker = document.createElement('div');
    this.picker.className = 'custom-datepicker';
    this.picker.style.display = 'none';
    document.body.appendChild(this.picker);

    // Stop all clicks inside picker from propagating
    this.picker.addEventListener('click', (e) => {
      e.stopPropagation();
    });

    // Event listeners
    this.input.addEventListener('focus', () => this.show());
    this.input.addEventListener('click', () => this.show());
    document.addEventListener('click', (e) => this.handleOutsideClick(e));

    // Render initial view
    this.render();
  }

  show() {
    this.picker.style.display = 'block';
    this.position();
    this.currentView = 'day';
    this.render();
  }

  hide() {
    this.picker.style.display = 'none';
  }

  position() {
    const rect = this.input.getBoundingClientRect();
    this.picker.style.position = 'absolute';
    this.picker.style.top = `${rect.bottom + window.scrollY + 4}px`;
    this.picker.style.left = `${rect.left + window.scrollX}px`;
    this.picker.style.zIndex = '9999';
  }

  handleOutsideClick(e) {
    if (!this.picker.contains(e.target) && e.target !== this.input) {
      this.hide();
    }
  }

  render() {
    this.picker.innerHTML = '';

    const header = this.createHeader();
    const body = this.createBody();

    this.picker.appendChild(header);
    this.picker.appendChild(body);
  }

  createHeader() {
    const header = document.createElement('div');
    header.className = 'cdp-header';

    const prevBtn = document.createElement('button');
    prevBtn.className = 'cdp-nav-btn';
    prevBtn.innerHTML = '‹';
    prevBtn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.navigate(-1);
    };

    const title = document.createElement('button');
    title.className = 'cdp-title';
    title.textContent = this.getHeaderTitle();
    title.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.switchView();
    };

    const nextBtn = document.createElement('button');
    nextBtn.className = 'cdp-nav-btn';
    nextBtn.innerHTML = '›';
    nextBtn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.navigate(1);
    };

    header.appendChild(prevBtn);
    header.appendChild(title);
    header.appendChild(nextBtn);

    return header;
  }

  getHeaderTitle() {
    const months = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'];

    if (this.currentView === 'day') {
      return `${months[this.viewDate.getMonth()]} ${this.viewDate.getFullYear()}`;
    } else if (this.currentView === 'month') {
      return `${this.viewDate.getFullYear()}`;
    } else {
      const startYear = Math.floor(this.viewDate.getFullYear() / 12) * 12;
      return `${startYear} - ${startYear + 11}`;
    }
  }

  switchView() {
    if (this.currentView === 'day') {
      this.currentView = 'month';
    } else if (this.currentView === 'month') {
      this.currentView = 'year';
    }
    this.render();
  }

  navigate(direction) {
    if (this.currentView === 'day') {
      this.viewDate.setMonth(this.viewDate.getMonth() + direction);
    } else if (this.currentView === 'month') {
      this.viewDate.setFullYear(this.viewDate.getFullYear() + direction);
    } else {
      this.viewDate.setFullYear(this.viewDate.getFullYear() + (direction * 12));
    }
    this.render();
  }

  createBody() {
    const body = document.createElement('div');
    body.className = 'cdp-body';

    if (this.currentView === 'day') {
      body.appendChild(this.createDayView());
    } else if (this.currentView === 'month') {
      body.appendChild(this.createMonthView());
    } else {
      body.appendChild(this.createYearView());
    }

    return body;
  }

  createDayView() {
    const container = document.createElement('div');
    container.className = 'cdp-day-view';

    // Weekday headers
    const weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
    const headerRow = document.createElement('div');
    headerRow.className = 'cdp-weekdays';
    weekdays.forEach(day => {
      const cell = document.createElement('div');
      cell.className = 'cdp-weekday';
      cell.textContent = day;
      headerRow.appendChild(cell);
    });
    container.appendChild(headerRow);

    // Days grid
    const daysGrid = document.createElement('div');
    daysGrid.className = 'cdp-days-grid';

    const year = this.viewDate.getFullYear();
    const month = this.viewDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Empty cells for days before month starts
    for (let i = 0; i < firstDay; i++) {
      const cell = document.createElement('div');
      cell.className = 'cdp-day cdp-day-empty';
      daysGrid.appendChild(cell);
    }

    // Days of month
    for (let day = 1; day <= daysInMonth; day++) {
      const cell = document.createElement('div');
      cell.className = 'cdp-day';
      cell.textContent = day;

      const cellDate = new Date(year, month, day);

      // Check if selected
      if (this.selectedDate &&
          cellDate.toDateString() === this.selectedDate.toDateString()) {
        cell.classList.add('cdp-day-selected');
      }

      // Check if today
      if (cellDate.toDateString() === new Date().toDateString()) {
        cell.classList.add('cdp-day-today');
      }

      // Check if disabled
      if (this.isDateDisabled(cellDate)) {
        cell.classList.add('cdp-day-disabled');
      } else {
        cell.onclick = (e) => {
          e.stopPropagation();
          this.selectDate(cellDate);
        };
      }

      daysGrid.appendChild(cell);
    }

    container.appendChild(daysGrid);
    return container;
  }

  createMonthView() {
    const container = document.createElement('div');
    container.className = 'cdp-month-view';

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    months.forEach((month, index) => {
      const cell = document.createElement('div');
      cell.className = 'cdp-month';
      cell.textContent = month;

      if (this.selectedDate &&
          this.selectedDate.getMonth() === index &&
          this.selectedDate.getFullYear() === this.viewDate.getFullYear()) {
        cell.classList.add('cdp-month-selected');
      }

      cell.onclick = (e) => {
        e.stopPropagation();
        this.selectMonth(index);
      };
      container.appendChild(cell);
    });

    return container;
  }

  createYearView() {
    const container = document.createElement('div');
    container.className = 'cdp-year-view';

    const startYear = Math.floor(this.viewDate.getFullYear() / 12) * 12;

    for (let i = 0; i < 12; i++) {
      const year = startYear + i;
      const cell = document.createElement('div');
      cell.className = 'cdp-year';
      cell.textContent = year;

      if (this.selectedDate && this.selectedDate.getFullYear() === year) {
        cell.classList.add('cdp-year-selected');
      }

      cell.onclick = (e) => {
        e.stopPropagation();
        this.selectYear(year);
      };
      container.appendChild(cell);
    }

    return container;
  }

  selectDate(date) {
    this.selectedDate = date;
    this.input.value = this.formatDate(date);
    this.hide();

    // Trigger change event
    const event = new Event('change', { bubbles: true });
    this.input.dispatchEvent(event);
  }

  selectMonth(month) {
    this.viewDate.setMonth(month);
    this.currentView = 'day';
    this.render();
  }

  selectYear(year) {
    this.viewDate.setFullYear(year);
    this.currentView = 'month';
    this.render();
  }

  isDateDisabled(date) {
    if (this.options.maxDate) {
      const maxDate = this.options.maxDate === 'today' ? new Date() : new Date(this.options.maxDate);
      maxDate.setHours(23, 59, 59, 999);
      if (date > maxDate) return true;
    }

    if (this.options.minDate) {
      const minDate = new Date(this.options.minDate);
      minDate.setHours(0, 0, 0, 0);
      if (date < minDate) return true;
    }

    return false;
  }

  formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  destroy() {
    if (this.picker && this.picker.parentNode) {
      this.picker.parentNode.removeChild(this.picker);
    }
  }
}

// Auto-initialize on date inputs with data-datepicker attribute
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('input[data-datepicker]').forEach(input => {
    new CustomDatePicker(input, {
      maxDate: input.dataset.maxDate || null,
      minDate: input.dataset.minDate || null
    });
  });
});
