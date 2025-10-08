/* Global common utilities for Review pages (I–V)
   - Provides ReviewUtils namespace and safe shims for common helpers
   - Non-breaking: if a function already exists on the page, we don't override it
*/
(function () {
  const ReviewUtils = {
    debounce(fn, delayMs) {
      let t;
      return function (...args) {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), delayMs);
      };
    },

    numeric: {
      validate(input) {
        if (!input || input.type !== 'number') return true;
        const max = parseFloat(input.getAttribute('max')) || Infinity;
        const min = parseFloat(input.getAttribute('min')) || 0;
        const value = parseFloat(input.value);
        if (input.value === '') {
          input.classList.remove('error');
          return true;
        }
        if (isNaN(value) || value < min) {
          input.value = '';
          input.classList.add('error');
          return false;
        }
        if (value > max) {
          input.value = max;
          input.classList.add('error');
          return false;
        }
        input.classList.remove('error');
        return true;
      },
    },

    table: {
      setupArrowNavigation(inputSelector) {
        const inputs = Array.from(document.querySelectorAll(inputSelector));
        if (inputs.length === 0) return;

        inputs.forEach((input) => {
          input.addEventListener('keydown', function (e) {
            if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) return;
            const currentInput = e.target;
            const table = currentInput.closest('table');
            if (!table) return;
            const tbody = table.querySelector('tbody');
            const tfoot = table.querySelector('tfoot');
            const rows = [...(tbody ? tbody.querySelectorAll('tr') : []), ...(tfoot ? tfoot.querySelectorAll('tr') : [])];
            const currentRow = currentInput.closest('tr');
            const currentRowIndex = rows.indexOf(currentRow);
            const currentCellIndex = Array.from(currentRow.querySelectorAll('input')).indexOf(currentInput);
            let targetInput = null;

            switch (e.key) {
              case 'ArrowUp':
                if (currentRowIndex > 0) {
                  const targetRow = rows[currentRowIndex - 1];
                  const targetInputs = targetRow.querySelectorAll('input');
                  if (targetInputs[currentCellIndex]) targetInput = targetInputs[currentCellIndex];
                }
                break;
              case 'ArrowDown':
                if (currentRowIndex < rows.length - 1) {
                  const targetRow = rows[currentRowIndex + 1];
                  const targetInputs = targetRow.querySelectorAll('input');
                  if (targetInputs[currentCellIndex]) targetInput = targetInputs[currentCellIndex];
                }
                break;
              case 'ArrowLeft':
                if (currentCellIndex > 0) {
                  const targetInputs = currentRow.querySelectorAll('input');
                  targetInput = targetInputs[currentCellIndex - 1];
                }
                break;
              case 'ArrowRight':
                if (currentCellIndex < currentRow.querySelectorAll('input').length - 1) {
                  const targetInputs = currentRow.querySelectorAll('input');
                  targetInput = targetInputs[currentCellIndex + 1];
                }
                break;
            }

            if (targetInput) {
              targetInput.focus();
              if (targetInput.select) targetInput.select();
              e.preventDefault();
            }
          });
        });
      },
    },

    header: {
      initHideOnScroll(options = {}) {
        let lastScrollTop = 0;
        const scrollThreshold = typeof options.scrollThreshold === 'number' ? options.scrollThreshold : 5;
        let isHeaderVisible = true;

        function handleScroll() {
          const header = document.querySelector('.page-header');
          if (!header) return;

          const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;

          if (Math.abs(currentScrollTop - lastScrollTop) < scrollThreshold) {
            return;
          }

          if (currentScrollTop > lastScrollTop && currentScrollTop > 100 && isHeaderVisible) {
            header.classList.add('hidden');
            isHeaderVisible = false;
          } else if (currentScrollTop < lastScrollTop && !isHeaderVisible) {
            header.classList.remove('hidden');
            isHeaderVisible = true;
          }

          if (currentScrollTop > 80) {
            header.classList.add('scrolled');
          } else {
            header.classList.remove('scrolled');
          }

          lastScrollTop = currentScrollTop;
        }

        let scrollTimer = null;
        function throttledScroll() {
          if (scrollTimer) return;
          scrollTimer = setTimeout(() => {
            handleScroll();
            scrollTimer = null;
          }, 10);
        }

        window.addEventListener('scroll', throttledScroll, { passive: true });
      },
    },

    menu: {
      initHamburgerMenu() {
        let menuOpen = false;
        function toggleMenu() {
          const menuToggle = document.querySelector('.menu-toggle');
          const menuDropdown = document.getElementById('menuDropdown');
          if (!menuToggle || !menuDropdown) return;

          menuOpen = !menuOpen;
          if (menuOpen) {
            menuToggle.classList.add('active');
            menuDropdown.classList.add('show');
          } else {
            menuToggle.classList.remove('active');
            menuDropdown.classList.remove('show');
          }
        }

        // Attach global for existing onclicks in templates
        if (!window.toggleMenu) {
          window.toggleMenu = toggleMenu;
        }

        document.addEventListener('click', function (event) {
          const menuContainer = document.querySelector('.menu-container');
          const menuDropdown = document.getElementById('menuDropdown');
          if (!menuContainer || !menuDropdown) return;
          if (!menuContainer.contains(event.target) && menuDropdown.classList.contains('show')) {
            toggleMenu();
          }
        });

        document.addEventListener('keydown', function (event) {
          const menuDropdown = document.getElementById('menuDropdown');
          if (event.key === 'Escape' && menuDropdown && menuDropdown.classList.contains('show')) {
            toggleMenu();
          }
        });

        // Highlight current page
        const currentPath = window.location.pathname;
        const menuItems = document.querySelectorAll('.menu-item');
        menuItems.forEach((item) => {
          if (item.getAttribute('href') === currentPath) {
            item.classList.add('current');
          }
        });
      },
    },

    api: {
      async fetchMemberCount(groupId, reviewNumber, fallback = 4) {
        if (!groupId) return fallback;
        try {
          const res = await fetch(`/api/attendance/${groupId}/${reviewNumber}`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          return data && Array.isArray(data.members) ? data.members.length : fallback;
        } catch (e) {
          console.error('fetchMemberCount error:', e);
          return fallback;
        }
      },

      async saveResponses(endpoint, payload) {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`Save failed: ${res.status}`);
        return res.json().catch(() => ({}));
      },

      async fetchResponses(groupId) {
        const res = await fetch(`/api/fetch-response/${encodeURIComponent(groupId)}`);
        if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
        return res.json();
      },
    },

    form: {
      autoFill(formEl, responses) {
        if (!responses) return 0;
        let filled = 0;
        for (const [fieldName, fieldValue] of Object.entries(responses)) {
          const elements = formEl.querySelectorAll(`[name="${CSS.escape(fieldName)}"]`);
          if (elements.length === 0) continue;
          elements.forEach((element) => {
            if (element.type === 'radio' || element.type === 'checkbox') {
              if (element.value === fieldValue) {
                element.checked = true;
                filled++;
              }
            } else {
              element.value = fieldValue;
              filled++;
            }
          });
        }
        return filled;
      },
    },
  };

  // Attach to window
  window.ReviewUtils = window.ReviewUtils || ReviewUtils;

  // Safe shims so existing pages can call these without refactor
  if (!window.validateInput) {
    window.validateInput = function (input) {
      return ReviewUtils.numeric.validate(input);
    };
  }
  if (!window.setupArrowNavigation) {
    window.setupArrowNavigation = function () {
      // default selector to all number inputs inside #performance-table
      ReviewUtils.table.setupArrowNavigation('#performance-table input[type="number"], #performance-table input[type="text"]');
    };
  }

  if (!window.initPageCommon) {
    window.initPageCommon = function () {
      try {
        ReviewUtils.menu.initHamburgerMenu();
        ReviewUtils.header.initHideOnScroll();
      } catch (e) {
        console.error('initPageCommon error:', e);
      }
    };
  }
})();


