/*
 * Needle & thread background.
 *
 * Any <canvas data-thread> gets a few sewing needles gliding across it,
 * each pulling a thread that leaves a trail of running stitches.
 *
 * Options (data attributes on the canvas):
 *   data-needles       how many needles (default 3)
 *   data-thread-color  thread colour (default gold)
 *   data-needle-color  needle colour (default silver)
 *
 * Pauses when off-screen or when the tab is hidden. Visitors who prefer
 * reduced motion get a still picture of stitches instead of an animation.
 */
(function () {
    "use strict";

    var canvases = document.querySelectorAll("canvas[data-thread]");
    if (!canvases.length) return;

    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var STITCH = 16;        // length of a visible stitch (px)
    var GAP = 10;           // gap where the thread is "under the fabric" (px)
    var TRAIL_LENGTH = 650; // how much thread stays visible behind a needle (px)
    var NEEDLE_LENGTH = 54;

    Array.prototype.forEach.call(canvases, setup);

    function setup(canvas) {
        var ctx = canvas.getContext("2d");
        var threadColor = canvas.dataset.threadColor || "#d4af37";
        var needleColor = canvas.dataset.needleColor || "#ededed";
        var count = parseInt(canvas.dataset.needles || "3", 10);

        var width = 0, height = 0;
        var needles = [];
        var visible = true;
        var lastTime = 0;
        var frame = null;

        function resize() {
            var dpr = Math.min(window.devicePixelRatio || 1, 2);
            width = canvas.clientWidth;
            height = canvas.clientHeight;
            canvas.width = Math.round(width * dpr);
            canvas.height = Math.round(height * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        function newNeedle(index, anywhere) {
            // Spread needles over different heights so their threads don't bunch up
            var band = (index + 0.5) / count;
            return {
                x: anywhere ? Math.random() * width : -NEEDLE_LENGTH * 2 - Math.random() * width * 0.5,
                baseY: height * (0.12 + 0.76 * band) + (Math.random() - 0.5) * height * 0.12,
                amp: 18 + Math.random() * 42,
                freq: 0.0035 + Math.random() * 0.004,
                phase: Math.random() * Math.PI * 2,
                speed: 55 + Math.random() * 55,          // px per second
                trail: [],                               // points the thread passes through
                travelled: 0
            };
        }

        function yAt(n, x) {
            return n.baseY + n.amp * Math.sin(n.freq * x + n.phase);
        }

        function step(n, dt) {
            var prevX = n.x, prevY = yAt(n, prevX);
            n.x += n.speed * dt;
            var y = yAt(n, n.x);
            var d = Math.hypot(n.x - prevX, y - prevY);
            n.travelled += d;

            var last = n.trail[n.trail.length - 1];
            if (!last || Math.hypot(n.x - last.x, y - last.y) > 5) {
                n.trail.push({ x: n.x, y: y, d: n.travelled });
            }

            // Drop thread that has scrolled out of the visible trail
            while (n.trail.length > 2 && n.travelled - n.trail[0].d > TRAIL_LENGTH) {
                n.trail.shift();
            }
        }

        function drawThread(n) {
            if (n.trail.length < 2) return;

            ctx.save();
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.strokeStyle = threadColor;

            // Running stitches. Each dash offset is the thread length at that point,
            // so stitches stay fixed to the fabric instead of crawling along
            ctx.lineWidth = 2;
            ctx.setLineDash([STITCH, GAP]);

            // Fade the thread out towards its tail in a few steps
            var steps = 4;
            var per = Math.ceil(n.trail.length / steps);
            for (var s = 0; s < steps; s++) {
                var from = s * per, to = Math.min(n.trail.length - 1, (s + 1) * per);
                if (to <= from) continue;
                ctx.globalAlpha = 0.18 + 0.62 * ((s + 1) / steps);
                ctx.lineDashOffset = n.trail[from].d;
                ctx.beginPath();
                ctx.moveTo(n.trail[from].x, n.trail[from].y);
                for (var i = from + 1; i <= to; i++) ctx.lineTo(n.trail[i].x, n.trail[i].y);
                ctx.stroke();
            }

            ctx.restore();
        }

        function drawNeedle(n) {
            var y = yAt(n, n.x);
            var ahead = yAt(n, n.x + 1);
            var angle = Math.atan2(ahead - y, 1);
            var half = NEEDLE_LENGTH / 2;

            ctx.save();
            ctx.translate(n.x, y);
            ctx.rotate(angle);

            // Short loose thread from the eye back to the last stitch
            ctx.strokeStyle = threadColor;
            ctx.lineWidth = 2;
            ctx.globalAlpha = 0.95;
            ctx.beginPath();
            ctx.moveTo(-half + 6, 0);
            ctx.quadraticCurveTo(-half - 10, 6, -half - 22, 2);
            ctx.stroke();

            // Needle body: tapered from the eye end to a sharp tip
            var gradient = ctx.createLinearGradient(0, -3, 0, 3);
            gradient.addColorStop(0, "#ffffff");
            gradient.addColorStop(0.45, needleColor);
            gradient.addColorStop(1, "#8c8c8c");
            ctx.fillStyle = gradient;
            ctx.strokeStyle = "rgba(0,0,0,0.35)";
            ctx.lineWidth = 0.6;
            ctx.beginPath();
            ctx.moveTo(half, 0);
            ctx.lineTo(-half + 4, -2.3);
            ctx.quadraticCurveTo(-half - 1, 0, -half + 4, 2.3);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            // The eye
            ctx.fillStyle = "rgba(0,0,0,0.55)";
            ctx.beginPath();
            ctx.ellipse(-half + 6, 0, 3.2, 0.9, 0, 0, Math.PI * 2);
            ctx.fill();

            ctx.restore();
        }

        function render() {
            ctx.clearRect(0, 0, width, height);
            needles.forEach(drawThread);
            needles.forEach(drawNeedle);
        }

        function tick(time) {
            frame = null;
            if (!visible || document.hidden) return;

            var dt = Math.min((time - (lastTime || time)) / 1000, 0.05);
            lastTime = time;

            needles.forEach(function (n, i) {
                step(n, dt);
                // Once the needle and its whole thread have left the screen, start a new one
                if (n.x - NEEDLE_LENGTH > width && (!n.trail.length || n.trail[0].x > width)) {
                    needles[i] = newNeedle(i, false);
                }
            });

            render();
            frame = requestAnimationFrame(tick);
        }

        function start() {
            if (frame === null && visible && !document.hidden) {
                lastTime = 0;
                frame = requestAnimationFrame(tick);
            }
        }

        function stillPicture() {
            // Reduced motion: lay each thread part-way across the screen and draw once
            needles.forEach(function (n) {
                n.x = -NEEDLE_LENGTH;
                n.trail = [];
                var target = width * (0.35 + Math.random() * 0.5);
                while (n.x < target) step(n, 1 / 30);
            });
            render();
        }

        resize();
        for (var i = 0; i < count; i++) needles.push(newNeedle(i, true));

        if (reduceMotion) {
            stillPicture();
            window.addEventListener("resize", function () { resize(); stillPicture(); });
            return;
        }

        // Pre-run a little so threads are already on screen when the page opens
        needles.forEach(function (n) {
            n.x -= 300;
            for (var s = 0; s < 300; s++) step(n, 1 / 60);
        });

        window.addEventListener("resize", function () {
            var oldWidth = width, oldHeight = height;
            resize();
            if (width === oldWidth && height === oldHeight) return;

            // Keep the threads already stitched; just stretch them to the new size
            var sx = oldWidth ? width / oldWidth : 1, sy = oldHeight ? height / oldHeight : 1;
            needles.forEach(function (n) {
                n.x *= sx;
                n.baseY *= sy;
                n.trail.forEach(function (p) { p.x *= sx; p.y *= sy; });
            });
            render();
        });

        if ("IntersectionObserver" in window) {
            new IntersectionObserver(function (entries) {
                visible = entries[0].isIntersecting;
                if (visible) start();
            }).observe(canvas);
        }

        document.addEventListener("visibilitychange", start);

        render();
        start();
    }
})();
