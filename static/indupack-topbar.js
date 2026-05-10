/**
 * Relógio da barra global (#hm-clock-time, #hm-clock-date).
 */
(function () {
    function tick() {
        var n = new Date();
        var t = document.getElementById("hm-clock-time");
        var d = document.getElementById("hm-clock-date");
        if (t) t.textContent = n.toLocaleTimeString("pt-BR", { hour12: false });
        if (d) {
            var day = n.toLocaleDateString("pt-BR", { weekday: "long" });
            day = day.charAt(0).toUpperCase() + day.slice(1);
            d.textContent =
                n.toLocaleDateString("pt-BR", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                }) +
                " | " +
                day;
        }
    }
    tick();
    setInterval(tick, 1000);
})();
