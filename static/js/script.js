// Find-My-Item Client Utilities

document.addEventListener('DOMContentLoaded', () => {
  // 1. Report Form Type Toggle
  const typeButtons = document.querySelectorAll('.type-toggle-btn');
  const typeInput = document.getElementById('itemTypeInput');

  if (typeButtons.length && typeInput) {
    const lostSelection = document.getElementById('lostReportSelection');
    const lostSelect = document.getElementById('lostItemSelect');
    const lostEmpty = document.getElementById('lostReportEmpty');
    const submitReport = document.getElementById('submitReportBtn');
    const itemName = document.getElementById('itemName');
    const category = document.getElementById('itemCategory');
    const location = document.getElementById('itemLocation');
    const date = document.getElementById('itemDate');
    const description = document.getElementById('itemDescription');
    const descriptionRequired = document.getElementById('foundDescriptionRequired');
    let eligibleLostReports = [];

    const loadEligibleLostReports = async () => {
      if (!lostSelect) return;
      lostSelect.disabled = true;
      lostSelect.innerHTML = '<option value="">Loading current lost reports…</option>';
      try {
        const response = await fetch('/api/eligible-lost-reports');
        const reports = await response.json();
        eligibleLostReports = response.ok ? reports : [];
        if (!eligibleLostReports.length) {
          lostSelect.innerHTML = '<option value="">No eligible lost reports</option>';
          if (lostEmpty) lostEmpty.hidden = false;
          if (submitReport) submitReport.disabled = true;
          return;
        }
        lostSelect.innerHTML = '<option value="" selected disabled>Select the matching lost report…</option>';
        eligibleLostReports.forEach((report) => {
          const option = document.createElement('option');
          option.value = report.id;
          option.textContent = `Case #${report.id}: ${report.item_name} — ${report.location} (${report.date})`;
          lostSelect.appendChild(option);
        });
        lostSelect.disabled = false;
        if (lostEmpty) lostEmpty.hidden = true;
        if (submitReport) submitReport.disabled = false;
      } catch (err) {
        lostSelect.innerHTML = '<option value="">Unable to load lost reports</option>';
        if (lostEmpty) lostEmpty.hidden = false;
        if (submitReport) submitReport.disabled = true;
      }
    };

    const populateSelectedLostDetails = () => {
      const report = eligibleLostReports.find((entry) => String(entry.id) === lostSelect.value);
      if (!report) return;
      // This gives the finder the original identifying values to verify. The
      // backend repeats the exact comparison and rejects any edited value.
      if (itemName) itemName.value = report.item_name;
      if (category) category.value = report.category;
      if (location) location.value = report.location;
      if (date) date.value = report.date;
      if (description) description.value = report.description;
    };

    if (lostSelect) {
      lostSelect.addEventListener('change', populateSelectedLostDetails);
    }

    typeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        typeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const selectedType = btn.dataset.type;
        typeInput.value = selectedType;

        const dynamicHelper = document.getElementById('typeHelperText');
        if (dynamicHelper) {
          if (selectedType === 'Lost') {
            dynamicHelper.textContent = 'Describe the item you lost so the finder or campus security can recognize it.';
          } else {
            dynamicHelper.textContent = 'Describe the item you discovered so the rightful owner can verify and claim it.';
          }
        }
        const isFound = selectedType === 'Found';
        if (lostSelection) lostSelection.hidden = !isFound;
        if (isFound) {
          if (lostSelect) lostSelect.required = true;
          if (description) description.required = true;
          if (descriptionRequired) descriptionRequired.hidden = false;
          loadEligibleLostReports();
        } else {
          if (lostSelect) {
            lostSelect.disabled = true;
            lostSelect.required = false;
            lostSelect.value = '';
          }
          if (description) description.required = false;
          if (descriptionRequired) descriptionRequired.hidden = true;
          if (lostEmpty) lostEmpty.hidden = true;
          if (submitReport) submitReport.disabled = false;
        }
      });
    });
  }

  // 2. File Upload Dropzone & Live Preview
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const previewImg = document.getElementById('previewImg');
  const dropzoneText = document.getElementById('dropzoneText');

  if (dropzone && fileInput) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files.length) {
        fileInput.files = files;
        handleFileSelect(files[0]);
      }
    });

    dropzone.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) {
        handleFileSelect(fileInput.files[0]);
      }
    });

    function handleFileSelect(file) {
      if (!file.type.match('image.*')) {
        alert('Please select an image file (JPG, JPEG, PNG, or WEBP).');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        if (previewImg) {
          previewImg.src = e.target.result;
          previewImg.style.display = 'block';
        }
        if (dropzoneText) {
          dropzoneText.innerHTML = `<strong>Selected:</strong> ${file.name} (${Math.round(file.size / 1024)} KB)<br><span style="color: var(--text-muted); font-size: 0.8rem;">Click or drag another image to replace</span>`;
        }
      };
      reader.readAsDataURL(file);
    }
  }

  // 3. Autofill Demo Accounts on Login
  window.fillDemoAccount = function(username, password) {
    const uInput = document.getElementById('loginUsername');
    const pInput = document.getElementById('loginPassword');
    if (uInput && pInput) {
      uInput.value = username;
      pInput.value = password;
    }
  };

  // 5. Live search suggestions (Flask /api/search)
  const searchInput = document.getElementById('mainSearchInput');
  const suggestionsBox = document.getElementById('searchSuggestions');
  let searchTimer = null;

  if (searchInput && suggestionsBox) {
    const hideSuggestions = () => suggestionsBox.classList.remove('active');

    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim();
      clearTimeout(searchTimer);
      if (q.length < 2) {
        hideSuggestions();
        suggestionsBox.innerHTML = '';
        return;
      }
      searchTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
          const items = await res.json();
          if (!items.length) {
            hideSuggestions();
            return;
          }
          suggestionsBox.innerHTML = items.map(item => `
            <a class="search-suggestion-item" href="/item/${item.id}">
              <img src="${item.image_path}" alt="" />
              <div>
                <div style="font-weight:600;font-size:0.9rem;">${item.item_name}</div>
                <div style="font-size:0.78rem;color:var(--text-muted);">${item.type} · ${item.location} · ${item.status}</div>
              </div>
            </a>
          `).join('');
          suggestionsBox.classList.add('active');
        } catch (err) {
          hideSuggestions();
        }
      }, 280);
    });

    document.addEventListener('click', (e) => {
      if (!suggestionsBox.contains(e.target) && e.target !== searchInput) {
        hideSuggestions();
      }
    });
  }

  // 6. Stagger case cards on feed
  document.querySelectorAll('.case-card').forEach((card, i) => {
    card.style.animationDelay = `${Math.min(i * 0.04, 0.4)}s`;
    card.classList.add('animate-in');
  });
});
