// OpenCue Documentation Search Implementation
// Using Lunr.js for client-side search

(function() {
  // Initialize search index
  var searchIndex = null;
  var searchData = null;
  var searchInput = document.getElementById('search-input');
  var searchResults = document.getElementById('search-results');
  var searchResultsContainer = document.getElementById('search-results-container');

  // Build search index
  function buildSearchIndex(data) {
    return lunr(function() {
      this.ref('id');
      this.field('title', { boost: 10 });
      this.field('content');
      this.field('keywords', { boost: 5 });
      this.field('description', { boost: 3 });

      data.forEach(function(doc) {
        this.add(doc);
      }, this);
    });
  }

  // Load search data
  function loadSearchData() {
    var xhr = new XMLHttpRequest();
    var baseUrl = document.querySelector('base') ? document.querySelector('base').getAttribute('href') : '';
    xhr.open('GET', (baseUrl || '') + '/search-data.json');
    xhr.onload = function() {
      if (xhr.status === 200) {
        searchData = JSON.parse(xhr.responseText);
        searchIndex = buildSearchIndex(searchData.docs);
      }
    };
    xhr.send();
  }

  // Perform search
  function performSearch(query) {
    if (!searchIndex || !query) {
      hideSearchResults();
      return;
    }

    var results = searchIndex.search(query);
    displaySearchResults(results, query);
  }

  // Display search results
  function displaySearchResults(results, query) {
    searchResults.innerHTML = '';

    if (results.length === 0) {
      searchResults.innerHTML = '<li class="search-no-results">No results found for "' + escapeHtml(query) + '"</li>';
      showSearchResults();
      return;
    }

    var resultsList = results.slice(0, 10).map(function(result) {
      var doc = searchData.docs.find(function(d) { return d.id === result.ref; });
      if (!doc) return '';

      var excerpt = createExcerpt(doc.content, query);
      var title = highlightMatches(doc.title, query);

      return '<li class="search-result-item">' +
        '<a href="' + doc.url + '" class="search-result-link">' +
        '<div class="search-result-title">' + title + '</div>' +
        '<div class="search-result-excerpt">' + excerpt + '</div>' +
        '</a>' +
        '</li>';
    }).join('');

    searchResults.innerHTML = resultsList;
    showSearchResults();
  }

  // Create excerpt with highlighted matches
  function createExcerpt(content, query) {
    var cleanContent = content.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
    var terms = query.toLowerCase().split(/\s+/);
    var excerptLength = 150;
    var bestIndex = -1;
    var bestScore = 0;

    // Find best matching position
    terms.forEach(function(term) {
      var index = cleanContent.toLowerCase().indexOf(term);
      if (index !== -1 && index > bestIndex) {
        bestIndex = index;
        bestScore++;
      }
    });

    // Extract excerpt around best match
    var start = Math.max(0, bestIndex - 50);
    var end = Math.min(cleanContent.length, start + excerptLength);
    var excerpt = cleanContent.substring(start, end);

    if (start > 0) excerpt = '...' + excerpt;
    if (end < cleanContent.length) excerpt = excerpt + '...';

    return highlightMatches(excerpt, query);
  }

  // Highlight matching terms
  function highlightMatches(text, query) {
    var terms = query.toLowerCase().split(/\s+/);
    var highlighted = text;

    terms.forEach(function(term) {
      var regex = new RegExp('(' + escapeRegExp(term) + ')', 'gi');
      highlighted = highlighted.replace(regex, '<mark>$1</mark>');
    });

    return highlighted;
  }

  // Show/hide search results
  function showSearchResults() {
    searchResultsContainer.style.display = 'block';
  }

  function hideSearchResults() {
    searchResultsContainer.style.display = 'none';
  }

  // Utility functions
  function escapeHtml(text) {
    var map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
  }

  function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // Debounce search input
  var searchTimeout;
  function debounceSearch(func, wait) {
    return function() {
      var context = this, args = arguments;
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(function() {
        func.apply(context, args);
      }, wait);
    };
  }

  // Event handlers
  if (searchInput) {
    // Initialize search
    loadSearchData();

    // Handle search input
    searchInput.addEventListener('input', debounceSearch(function(e) {
      var query = e.target.value.trim();
      if (query.length >= 2) {
        performSearch(query);
      } else {
        hideSearchResults();
      }
    }, 300));

    // Handle keyboard navigation
    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        searchInput.value = '';
        hideSearchResults();
        searchInput.blur();
      }
    });

    // Close search results when clicking outside
    document.addEventListener('click', function(e) {
      if (!searchInput.contains(e.target) && !searchResultsContainer.contains(e.target)) {
        hideSearchResults();
      }
    });
  }
})();