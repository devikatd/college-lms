/**
 * Dynamic Cascading Dropdown Engine (Vanilla JS)
 *
 * Connects dependent HTML select elements to asynchronously fetch
 * options from backend APIs without triggering page reloads.
 *
 * Supported cascades:
 * - Department -> Program (/academics/api/departments/{id}/programs/)
 * - Program -> Scheme (/academics/api/programs/{id}/schemes/)
 * - Scheme -> Semester (/academics/api/schemes/{id}/semesters/)
 * - Semester -> Course (/academics/api/semesters/{id}/courses/)
 */

class CascadingSelect {
    /**
     * @param {Object} config
     * @param {string} config.parentSelector
     * @param {string} config.childSelector
     * @param {Function} config.endpointFn - (parentId) => string URL
     * @param {Function} config.labelFn - (item) => string option label
     * @param {string} [config.placeholder] - Default option text
     */
    constructor(config) {
        this.parentElement = document.querySelector(config.parentSelector);
        this.childElement = document.querySelector(config.childSelector);
        this.endpointFn = config.endpointFn;
        this.labelFn = config.labelFn || ((item) => item.name || item.title || item.code);
        this.placeholder = config.placeholder || '-- Select an option --';

        if (this.parentElement && this.childElement) {
            this.init();
        }
    }

    init() {
        this.parentElement.addEventListener('change', () => this.handleChange());
    }

    async handleChange() {
        const parentId = this.parentElement.value;

        // Reset child select
        this.childElement.innerHTML = `<option value="">${this.placeholder}</option>`;

        if (!parentId) {
            this.childElement.disabled = true;
            return;
        }

        this.childElement.disabled = true;
        const originalChildPlaceholder = this.childElement.options[0].text;
        this.childElement.options[0].text = 'Loading options...';

        try {
            const url = this.endpointFn(parentId);
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();
            const items = data.results || [];

            this.childElement.innerHTML = `<option value="">${this.placeholder}</option>`;

            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = this.labelFn(item);
                this.childElement.appendChild(opt);
            });

            this.childElement.disabled = false;
            // Trigger change on child in case further cascade levels exist
            this.childElement.dispatchEvent(new Event('change'));

        } catch (error) {
            console.error('CascadingSelect fetch error:', error);
            this.childElement.innerHTML = `<option value="">Error loading options</option>`;
            this.childElement.disabled = true;
        }
    }
}

// Global initialization helper
window.initCascadingAcademicSelects = function(options = {}) {
    const deptSelector = options.deptSelector || '#id_department';
    const progSelector = options.progSelector || '#id_program';
    const schemeSelector = options.schemeSelector || '#id_scheme';
    const semSelector = options.semSelector || '#id_semester';

    // 1. Dept -> Program
    if (document.querySelector(deptSelector) && document.querySelector(progSelector)) {
        new CascadingSelect({
            parentSelector: deptSelector,
            childSelector: progSelector,
            endpointFn: (deptId) => `/academics/api/departments/${deptId}/programs/`,
            labelFn: (prog) => `${prog.name} (${prog.code})`,
            placeholder: '-- Select Degree Program --'
        });
    }

    // 2. Program -> Scheme
    if (document.querySelector(progSelector) && document.querySelector(schemeSelector)) {
        new CascadingSelect({
            parentSelector: progSelector,
            childSelector: schemeSelector,
            endpointFn: (progId) => `/academics/api/programs/${progId}/schemes/`,
            labelFn: (scheme) => `${scheme.name} [${scheme.code}]`,
            placeholder: '-- Select Curriculum Scheme --'
        });
    }

    // 3. Scheme -> Semester
    if (document.querySelector(schemeSelector) && document.querySelector(semSelector)) {
        new CascadingSelect({
            parentSelector: schemeSelector,
            childSelector: semSelector,
            endpointFn: (schemeId) => `/academics/api/schemes/${schemeId}/semesters/`,
            labelFn: (sem) => `Semester ${sem.semester_number} (${sem.semester_type})`,
            placeholder: '-- Select Semester --'
        });
    }
};

document.addEventListener('DOMContentLoaded', function() {
    window.initCascadingAcademicSelects();
});
