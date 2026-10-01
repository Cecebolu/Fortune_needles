/*
 * Needle & thread background.
 *
 * Any <canvas data-thread> gets a few sewing needles gliding across it,
 * each pulling a thread that leaves a trail of running stitches.
 *
 * Pointing at (or tabbing to) a button in the same section sends the nearest
 * needle over to stitch a ring of thread around it; then it carries on its way
 * and the ring slowly unravels. While it does this the needle is drawn on a
 * second, transparent layer above the page, so cards don't hide the ring.
 *
 * Options (data attributes on the canvas):
 *   data-needles   how many needles (default 3)
 *   data-palette   "dark" (bright threads, for dark backgrounds, default)
 *                  or "light" (deeper threads, for light backgrounds)
 *
 * Every needle gets its own thread colour and metal, so the colours mix.
 *
 * Pauses when off-screen or when the tab is hidden. Visitors who prefer
 * reduced motion get a still picture of stitches instead of an animation.
 */
(function () {
    "use strict";

    var canvases = document.querySelectorAll("canvas[data-thread]");
    if (!canvases.length) return;

    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var STITCH = 16;            // length of a visible stitch (px)
    var GAP = 10;               // gap where the thread is "under the fabric" (px)
    var TRAIL_LENGTH = 650;     // how much thread stays visible behind a wandering needle (px)
    var NEEDLE_LENGTH = 54;
    var APPROACH_SPEED = 620;   // px/s when swooping to a button
    var STITCH_SPEED = 420;     // px/s while stitching around a button
    var UNRAVEL_SPEED = 140;    // px/s the extra thread is pulled away afterwards
    var RING_GAP = 7;           // space between the button's corners and the ring (px)

    var THREAD_COLOURS = {
        dark:  ["#e9c46a", "#ff4d6d", "#2ec4b6", "#c77dff", "#ff8fab", "#4cc9f0", "#f4a261", "#80ed99"],
        light: ["#b8860b", "#c1121f", "#13867f", "#7b2cbf", "#d63384", "#1d4ed8", "#d9480f", "#2b9348"]
    };

    // Needle metals: [highlight, body, shadow]
    var METALS = [
        ["#ffffff", "#e6e6e6", "#8c8c8c"],   // silver
        ["#fff4c2", "#d4af37", "#8a6a12"],   // gold
        ["#ffe3d8", "#d99a84", "#8c5443"]    // rose gold
    ];

    Array.prototype.forEach.call(canvases, setup);

    function setup(canvas) {
        var back = canvas.getContext("2d");

        var frontCanvas = document.createElement("canvas");
        frontCanvas.className = "thread-canvas thread-canvas-front";
        frontCanvas.setAttribute("aria-hidden", "true");
        canvas.parentElement.appendChild(frontCanvas);
        var front = frontCanvas.getContext("2d");
        var palette = THREAD_COLOURS[canvas.dataset.palette] || THREAD_COLOURS.dark;
        var count = parseInt(canvas.dataset.needles || "3", 10);
        var colourTurn = Math.floor(Math.random() * palette.length);

        // Hand out colours in turn so needles on screen together never share one
        function nextColour() {
            colourTurn = (colourTurn + 1) % palette.length;
            return palette[colourTurn];
        }

        var width = 0, height = 0;
        var needles = [];
        var visible = true;
        var lastTime = 0;
        var frame = null;

        function resize() {
            var dpr = Math.min(window.devicePixelRatio || 1, 2);
            width = canvas.clientWidth;
            height = canvas.clientHeight;
            [[canvas, back], [frontCanvas, front]].forEach(function (layer) {
                layer[0].width = Math.round(width * dpr);
                layer[0].height = Math.round(height * dpr);
                layer[1].setTransform(dpr, 0, 0, dpr, 0, 0);
            });
        }

        // ------------------------------------------------------------------
        // Needles
        // ------------------------------------------------------------------

        function newNeedle(index, anywhere) {
            // Spread needles over different heights so their threads don't bunch up
            var band = (index + 0.5) / count;
            var n = {
                x: anywhere ? Math.random() * width : -NEEDLE_LENGTH * 2 - Math.random() * width * 0.5,
                y: 0,
                angle: 0,
                baseY: height * (0.12 + 0.76 * band) + (Math.random() - 0.5) * height * 0.12,
                amp: 18 + Math.random() * 42,
                freq: 0.0035 + Math.random() * 0.004,
                phase: Math.random() * Math.PI * 2,
                speed: 55 + Math.random() * 55,          // px per second while wandering
                mode: "wander",                          // "wander" | "approach" | "stitch"
                ring: null,                              // the button ring being stitched
                inFront: false,                          // drawn above the page while stitching
                maxTrail: TRAIL_LENGTH,
                trail: [],                               // points the thread passes through
                travelled: 0,
                thread: nextColour(),
                metal: METALS[Math.floor(Math.random() * METALS.length)]
            };
            n.y = waveY(n, n.x);
            return n;
        }

        function waveY(n, x) {
            return n.baseY + n.amp * Math.sin(n.freq * x + n.phase);
        }

        function ringPoint(ring, t) {
            return { x: ring.cx + ring.rx * Math.cos(t), y: ring.cy + ring.ry * Math.sin(t) };
        }

        // Go back to gliding along a wave that starts exactly where the needle is now
        function resumeWander(n) {
            n.mode = "wander";
            n.ring = null;
            n.baseY = n.y - n.amp * Math.sin(n.freq * n.x + n.phase);
        }

        function moveTo(n, x, y) {
            var dx = x - n.x, dy = y - n.y;
            var d = Math.hypot(dx, dy);
            if (d > 0.01) {
                // Turn smoothly towards the direction of travel
                var target = Math.atan2(dy, dx);
                var turn = Math.atan2(Math.sin(target - n.angle), Math.cos(target - n.angle));
                n.angle += turn * Math.min(1, 0.35 + d / 40);
            }
            n.x = x;
            n.y = y;
            n.travelled += d;

            var last = n.trail[n.trail.length - 1];
            if (!last || Math.hypot(x - last.x, y - last.y) > 4) {
                n.trail.push({ x: x, y: y, d: n.travelled });
            }
        }

        function step(n, dt) {
            if (n.mode === "wander") {
                var nx = n.x + n.speed * dt;
                moveTo(n, nx, waveY(n, nx));

                // After stitching, pull the extra thread away gradually so the ring unravels
                if (n.maxTrail > TRAIL_LENGTH) {
                    n.maxTrail = Math.max(TRAIL_LENGTH, n.maxTrail - UNRAVEL_SPEED * dt);
                } else if (n.inFront) {
                    n.inFront = false;
                }

            } else if (n.mode === "approach") {
                var start = ringPoint(n.ring, n.ring.t0);
                var dx = start.x - n.x, dy = start.y - n.y;
                var dist = Math.hypot(dx, dy);
                var move = APPROACH_SPEED * dt;
                if (dist <= move) {
                    moveTo(n, start.x, start.y);
                    n.mode = "stitch";
                    n.ring.swept = 0;
                } else {
                    moveTo(n, n.x + dx / dist * move, n.y + dy / dist * move);
                }

            } else if (n.mode === "stitch") {
                var ring = n.ring;
                ring.swept += STITCH_SPEED * dt / ring.avgRadius;
                var p = ringPoint(ring, ring.t0 + ring.dir * ring.swept);
                moveTo(n, p.x, p.y);
                // One full loop plus a little overlap, then carry on
                if (ring.swept >= Math.PI * 2.12) resumeWander(n);
            }

            // Drop thread that has been pulled out of view
            while (n.trail.length > 2 && n.travelled - n.trail[0].d > n.maxTrail) {
                n.trail.shift();
            }
        }

        // ------------------------------------------------------------------
        // Stitching around buttons
        // ------------------------------------------------------------------

        function ringAround(button) {
            var box = canvas.getBoundingClientRect();
            var r = button.getBoundingClientRect();
            if (!r.width || !r.height) return null;

            var cx = r.left - box.left + r.width / 2;
            var cy = r.top - box.top + r.height / 2;
            if (cx < 0 || cy < 0 || cx > width || cy > height) return null;

            // An oval through the button's corners is the rectangle's half-size times sqrt(2);
            // a small gap on top keeps the thread clear of the rounded corners
            var rx = r.width / 2 * Math.SQRT2 + RING_GAP;
            var ry = r.height / 2 * Math.SQRT2 + RING_GAP;
            return { button: button, cx: cx, cy: cy, rx: rx, ry: ry, avgRadius: Math.sqrt((rx * rx + ry * ry) / 2) };
        }

        function stitchAround(button) {
            if (needles.some(function (n) { return n.ring && n.ring.button === button; })) return;

            var ring = ringAround(button);
            if (!ring) return;

            // The nearest free needle that is on (or close to) the screen
            var best = null, bestDistance = Infinity;
            needles.forEach(function (n) {
                if (n.mode !== "wander" || n.x < -NEEDLE_LENGTH * 2 || n.x > width + NEEDLE_LENGTH) return;
                var d = Math.hypot(n.x - ring.cx, n.y - ring.cy);
                if (d < bestDistance) { best = n; bestDistance = d; }
            });
            if (!best) return;

            // Join the ring at the point nearest the needle, and go round in its direction of travel
            ring.t0 = Math.atan2((best.y - ring.cy) / ring.ry, (best.x - ring.cx) / ring.rx);
            ring.dir = best.y < ring.cy ? 1 : -1;

            best.ring = ring;
            best.mode = "approach";
            best.inFront = true;
            // Keep the whole ring (and the swoop to it) visible until the needle leaves
            best.maxTrail = Math.max(best.maxTrail, bestDistance + 2 * Math.PI * ring.avgRadius + 260);

            start();
        }

        function cancelApproach(button) {
            needles.forEach(function (n) {
                // A needle already stitching finishes its loop; one still on its way turns back
                if (n.mode === "approach" && n.ring && n.ring.button === button) resumeWander(n);
            });
        }

        if (!reduceMotion) {
            var section = canvas.parentElement;
            section.querySelectorAll(".btn").forEach(function (button) {
                button.addEventListener("mouseenter", function () { stitchAround(button); });
                button.addEventListener("focus", function () { stitchAround(button); });
                button.addEventListener("mouseleave", function () { cancelApproach(button); });
                button.addEventListener("blur", function () { cancelApproach(button); });
            });
        }

        // ------------------------------------------------------------------
        // Drawing
        // ------------------------------------------------------------------

        function drawThread(n) {
            if (n.trail.length < 2) return;
            var ctx = n.inFront ? front : back;

            ctx.save();
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.strokeStyle = n.thread;

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
            var half = NEEDLE_LENGTH / 2;
            var ctx = n.inFront ? front : back;

            ctx.save();
            ctx.translate(n.x, n.y);
            ctx.rotate(n.angle);

            // Short loose thread from the eye back to the last stitch
            ctx.strokeStyle = n.thread;
            ctx.lineWidth = 2;
            ctx.globalAlpha = 0.95;
            ctx.beginPath();
            ctx.moveTo(-half + 6, 0);
            ctx.quadraticCurveTo(-half - 10, 6, -half - 22, 2);
            ctx.stroke();

            // Needle body: tapered from the eye end to a sharp tip
            var gradient = ctx.createLinearGradient(0, -3, 0, 3);
            gradient.addColorStop(0, n.metal[0]);
            gradient.addColorStop(0.45, n.metal[1]);
            gradient.addColorStop(1, n.metal[2]);
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
            back.clearRect(0, 0, width, height);
            front.clearRect(0, 0, width, height);
            needles.forEach(drawThread);
            needles.forEach(drawNeedle);
        }

        // ------------------------------------------------------------------
        // Animation loop
        // ------------------------------------------------------------------

        function tick(time) {
            frame = null;
            if (!visible || document.hidden) return;

            var dt = Math.min((time - (lastTime || time)) / 1000, 0.05);
            lastTime = time;

            needles.forEach(function (n, i) {
                step(n, dt);
                // Once a wandering needle and its whole thread have left the screen, start a new one
                if (n.mode === "wander" && n.x - NEEDLE_LENGTH > width && (!n.trail.length || n.trail[0].x > width)) {
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
                n.y = waveY(n, n.x);
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
            n.y = waveY(n, n.x);
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
                n.y *= sy;
                n.baseY *= sy;
                n.trail.forEach(function (p) { p.x *= sx; p.y *= sy; });
                if (n.mode !== "wander") resumeWander(n);
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
