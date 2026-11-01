(function () {
  "use strict";

  var feed = document.querySelector(".news-feed");
  if (!feed) return;

  var cards = Array.prototype.slice.call(feed.querySelectorAll(".news-card"));
  var navigation = feed.querySelector(".news-pagination");
  var status = feed.querySelector(".news-feed__status");
  var start = feed.querySelector(".news-feed__start");
  var pageSize = Number(feed.dataset.pageSize) || 10;
  var pageCount = Math.max(1, Math.ceil(cards.length / pageSize));
  var currentPage = 1;

  function readPage() {
    var value = new URL(window.location.href).searchParams.get("page");
    var number = value && /^\d+$/.test(value) ? Number(value) : 1;
    return Math.min(pageCount, Math.max(1, number));
  }

  function pageUrl(page) {
    var url = new URL(window.location.href);
    if (page === 1) url.searchParams.delete("page");
    else url.searchParams.set("page", String(page));
    return url.pathname + url.search + url.hash;
  }

  function pageLink(label, page, disabled, isCurrent) {
    var link = document.createElement("a");
    link.textContent = label;
    if (disabled) {
      link.setAttribute("aria-disabled", "true");
      link.setAttribute("role", "link");
    } else {
      link.href = pageUrl(page);
      link.dataset.newsPage = String(page);
      link.setAttribute("aria-label", /^\d+$/.test(label) ? "第 " + page + " 页" : label);
    }
    if (isCurrent) link.setAttribute("aria-current", "page");
    return link;
  }

  function render(page, moveToStart) {
    currentPage = page;
    cards.forEach(function (card, index) {
      card.hidden = index < (page - 1) * pageSize || index >= page * pageSize;
    });
    status.textContent = "共 " + cards.length + " 条新闻 · 第 " + page + " / " + pageCount + " 页";
    navigation.textContent = "";
    navigation.appendChild(pageLink("上一页", page - 1, page === 1, false));
    for (var i = 1; i <= pageCount; i += 1) {
      navigation.appendChild(pageLink(String(i), i, false, i === page));
    }
    navigation.appendChild(pageLink("下一页", page + 1, page === pageCount, false));
    navigation.hidden = pageCount <= 1;
    if (moveToStart) {
      start.focus({ preventScroll: true });
      feed.scrollIntoView({ block: "start" });
    }
  }

  navigation.addEventListener("click", function (event) {
    var link = event.target.closest("a[data-news-page]");
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    var page = Number(link.dataset.newsPage);
    if (page === currentPage) return;
    window.history.pushState(null, "", pageUrl(page));
    render(page, true);
  });

  window.addEventListener("popstate", function () {
    render(readPage(), false);
  });

  var initialPage = readPage();
  window.history.replaceState(window.history.state, "", pageUrl(initialPage));
  render(initialPage, false);
})();
