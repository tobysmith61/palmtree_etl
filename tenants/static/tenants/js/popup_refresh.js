if (window.opener && window.location.search.includes("_popup=1")) {
    window.addEventListener("unload", function () {
        window.opener.location.reload();
    });
}