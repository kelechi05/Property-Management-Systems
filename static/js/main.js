// Hero Slider Functionality
let currentSlideIndex = 1;

function prevSlide() {
  const slides = document.querySelectorAll('.slide');
  if (slides.length > 0) {
    currentSlideIndex--;
    showSlides(currentSlideIndex);
  }
}

function nextSlide() {
  const slides = document.querySelectorAll('.slide');
  if (slides.length > 0) {
    currentSlideIndex++;
    showSlides(currentSlideIndex);
  }
}

function currentSlide(n) {
  currentSlideIndex = n;
  showSlides(currentSlideIndex);
}

function showSlides(n) {
  const slides = document.querySelectorAll('.slide');
  const dots = document.querySelectorAll('.dot');
  
  if (slides.length === 0) return;

  // Wrap around if index is out of bounds
  if (n > slides.length) {
    currentSlideIndex = 1;
  }
  if (n < 1) {
    currentSlideIndex = slides.length;
  }

  // Remove active class from all slides
  slides.forEach(slide => {
    slide.classList.remove('active');
  });

  // Remove active class from all dots
  dots.forEach(dot => {
    dot.classList.remove('active');
  });

  // Add active class to current slide and corresponding dot
  slides[currentSlideIndex - 1].classList.add('active');
  if (dots.length > 0) {
    dots[currentSlideIndex - 1].classList.add('active');
  }
}

// Initialize slider on page load
document.addEventListener('DOMContentLoaded', function() {
  const slides = document.querySelectorAll('.slide');
  if (slides.length > 0) {
    // Show first slide initially
    showSlides(currentSlideIndex);
    
    // Auto-advance slides every 5 seconds if there are multiple slides
    if (slides.length > 1) {
      setInterval(function() {
        currentSlideIndex++;
        showSlides(currentSlideIndex);
      }, 5000);
    }
  }

  const welcomeSection = document.querySelector('.welcome-note');
  if (welcomeSection) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      welcomeSection.classList.add('is-visible');
    } else if ('IntersectionObserver' in window) {
      const welcomeObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) {
            return;
          }

          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        });
      }, {
        threshold: 0.3,
        rootMargin: '0px 0px -10% 0px',
      });

      welcomeObserver.observe(welcomeSection);
    } else {
      welcomeSection.classList.add('is-visible');
    }
  }

  function getCookie(name) {
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : null;
  }

  const notificationCenters = document.querySelectorAll('[data-notification-center]');
  notificationCenters.forEach(center => {
    const markSeenUrl = center.dataset.markSeenUrl;

    function updateNotificationCount() {
      const unreadItems = center.querySelectorAll('[data-notification-item].is-unread').length;
      const countBadge = center.querySelector('[data-notification-count]');
      if (unreadItems <= 0) {
        if (countBadge) {
          countBadge.remove();
        }
        return;
      }

      if (countBadge) {
        countBadge.textContent = unreadItems;
      }
    }

    center.querySelectorAll('[data-notification-item]').forEach(item => {
      item.addEventListener('click', function(event) {
        if (item.dataset.seenPosted === 'true' || !item.classList.contains('is-unread')) {
          return;
        }

        event.preventDefault();
        const notificationKey = item.dataset.notificationKey;
        if (!notificationKey) {
          window.location.href = item.href;
          return;
        }

        fetch(markSeenUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken') || '',
          },
          body: JSON.stringify({ notification_keys: [notificationKey] }),
        })
          .then(response => {
            if (!response.ok) {
              throw new Error('Failed to mark notification as seen.');
            }
            return response.json();
          })
          .then(() => {
            item.dataset.seenPosted = 'true';
            item.classList.remove('is-unread');
            updateNotificationCount();
            window.location.href = item.href;
          })
          .catch(() => {
            window.location.href = item.href;
          });
      });
    });
  });

  document.querySelectorAll('.dashboard-table-row-link[data-href]').forEach(row => {
    const goToRowLink = () => {
      if (row.dataset.href) {
        window.location.href = row.dataset.href;
      }
    };

    row.addEventListener('click', event => {
      if (event.target.closest('[data-row-link-ignore], a, button, input, select, textarea, label')) {
        return;
      }
      goToRowLink();
    });

    row.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        goToRowLink();
      }
    });
  });
});
