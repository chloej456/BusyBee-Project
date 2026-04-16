document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const searchResults = document.getElementById("searchResults");

    const suggestedSearches = [
        "Festivals", "Sport", "Croke Park", "Dua Lipa", "GAA", "Robbie Williams"
    ];

    function showSuggestions() {
        const query = searchInput.value.toLowerCase().trim();
        searchResults.innerHTML = suggestedSearches
            .filter(item => item.toLowerCase().includes(query))
            .map(item => `<div class="result-item suggestion"><i class="fa fa-search"></i> ${item}</div>`)
            .join("");

        searchResults.style.display = query ? "block" : "none"; // Only show if there's input
    }

    function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        window.location.href = `/search_results/?query=${encodeURIComponent(query)}`;
    }

    // Event Listeners
    searchInput.addEventListener("input", showSuggestions);
    searchInput.addEventListener("focus", showSuggestions);
    searchButton.addEventListener("click", performSearch);

    searchResults.addEventListener("click", function (e) {
        if (e.target.classList.contains("suggestion")) {
            searchInput.value = e.target.textContent.trim();
            performSearch();
        }
    });

    document.addEventListener("click", function (e) {
        if (!searchResults.contains(e.target) && e.target !== searchInput) {
            searchResults.style.display = "none";
        }
    });

    // Enable "Enter" keypress to trigger search
    searchInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
            performSearch();
        }
    });
});
