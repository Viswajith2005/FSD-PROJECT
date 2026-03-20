// ═══════════════════════════════════════
// LOST & FOUND PORTAL — main.js
// Design: Miruro-inspired interactions
// ═══════════════════════════════════════

$(document).ready(function () {

  // ── 1. Navbar scroll class ──────────────────
  const $navbar = $('#main-navbar');
  $(window).on('scroll.navbar', function () {
    if ($(this).scrollTop() > 20) {
      $navbar.addClass('scrolled');
    } else {
      $navbar.removeClass('scrolled');
    }
  });

  // ── 2. Back to top button ──────────────────
  const $btt = $('#backToTop');
  $(window).on('scroll.btt', function () {
    if ($(this).scrollTop() > 400) {
      $btt.addClass('visible');
    } else {
      $btt.removeClass('visible');
    }
  });

  $btt.on('click', function () {
    $('html, body').animate({ scrollTop: 0 }, 400);
  });

  // ── 3. Scroll Reveal (IntersectionObserver) ──
  if ('IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.reveal').forEach(function (el) {
      revealObserver.observe(el);
    });
  } else {
    // Fallback for older browsers
    document.querySelectorAll('.reveal').forEach(function (el) {
      el.classList.add('visible');
    });
  }

  // ── 4. Parallax on hero glow orbs ──────────
  const glow1 = document.querySelector('.glow-1');
  const glow2 = document.querySelector('.glow-2');
  const glow3 = document.querySelector('.glow-3');

  if (glow1 || glow2 || glow3) {
    document.addEventListener('mousemove', function (e) {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      const dx = (e.clientX - cx) / cx;
      const dy = (e.clientY - cy) / cy;

      if (glow1) glow1.style.transform = `translateX(calc(-50% + ${dx * 18}px)) translateY(${dy * 18}px)`;
      if (glow2) glow2.style.transform = `translate(${dx * -14}px, ${dy * -14}px)`;
      if (glow3) glow3.style.transform = `translate(${dx * 11}px, ${dy * 11}px)`;
    });
  }

  // ── 5. Form Validation ──────────────────────

  // Login form
  $('#loginForm').on('submit', function (e) {
    let valid = true;

    const email = $('#loginEmail').val().trim();
    const password = $('#loginPassword').val();

    if (!email) {
      showFieldError('#loginEmail', 'Email is required.');
      valid = false;
    } else if (!isValidEmail(email)) {
      showFieldError('#loginEmail', 'Enter a valid email address.');
      valid = false;
    } else {
      clearFieldError('#loginEmail');
    }

    if (!password) {
      showFieldError('#loginPassword', 'Password is required.');
      valid = false;
    } else {
      clearFieldError('#loginPassword');
    }

    if (!valid) e.preventDefault();
  });

  // Signup form
  $('#signupForm').on('submit', function (e) {
    let valid = true;

    const name = $('#signupName').val().trim();
    const email = $('#signupEmail').val().trim();
    const password = $('#signupPassword').val();
    const confirm = $('#signupConfirm').val();

    if (!name || name.length < 2) {
      showFieldError('#signupName', 'Name must be at least 2 characters.');
      valid = false;
    } else {
      clearFieldError('#signupName');
    }

    if (!email) {
      showFieldError('#signupEmail', 'Email is required.');
      valid = false;
    } else if (!isValidEmail(email)) {
      showFieldError('#signupEmail', 'Enter a valid email address.');
      valid = false;
    } else {
      clearFieldError('#signupEmail');
    }

    if (!password || password.length < 6) {
      showFieldError('#signupPassword', 'Password must be at least 6 characters.');
      valid = false;
    } else {
      clearFieldError('#signupPassword');
    }

    if (confirm !== password) {
      showFieldError('#signupConfirm', 'Passwords do not match.');
      valid = false;
    } else {
      clearFieldError('#signupConfirm');
    }

    if (!valid) e.preventDefault();
  });

  // Report form
  $('#reportForm').on('submit', function (e) {
    let valid = true;

    const title = $('#reportTitle').val().trim();
    const desc = $('#reportDesc').val().trim();
    const location = $('#reportLocation').val().trim();
    const date = $('#reportDate').val();

    if (!title) {
      showFieldError('#reportTitle', 'Title is required.'); valid = false;
    } else { clearFieldError('#reportTitle'); }

    if (!desc || desc.length < 10) {
      showFieldError('#reportDesc', 'Description must be at least 10 characters.'); valid = false;
    } else { clearFieldError('#reportDesc'); }

    if (!location) {
      showFieldError('#reportLocation', 'Location is required.'); valid = false;
    } else { clearFieldError('#reportLocation'); }

    if (!date) {
      showFieldError('#reportDate', 'Date is required.'); valid = false;
    } else { clearFieldError('#reportDate'); }

    if (!valid) e.preventDefault();
  });

  // ── 6. Confirmations ──────────────────
  $(document).on('click', '.confirm-delete', function (e) {
    if (!confirm('Are you sure you want to delete this item? This cannot be undone.')) {
      e.preventDefault();
    }
  });

  $(document).on('click', '.confirm-resolve', function (e) {
    if (!confirm('Are you sure you want to mark this item as resolved?')) {
      e.preventDefault();
    }
  });

  // ── 7. Auto-dismiss alerts ──────────────────
  setTimeout(function () {
    $('.glass-alert').fadeOut(600);
  }, 4000);

  // ─────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────
  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function showFieldError(selector, msg) {
    const $el = $(selector);
    $el.addClass('is-invalid');
    let $fb = $el.siblings('.invalid-feedback');
    if (!$fb.length) {
      $fb = $('<div class="invalid-feedback"></div>');
      $el.after($fb);
    }
    $fb.text(msg);
  }

  function clearFieldError(selector) {
    const $el = $(selector);
    $el.removeClass('is-invalid');
    $el.siblings('.invalid-feedback').remove();
  }

});
