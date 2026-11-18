# Layout checks for app-check

People use these apps on Windows and Mac laptops, on external monitors when
docked, and sometimes with the window snapped to half a screen. Display
scaling and browser zoom mean the page a browser gets is smaller than the
screen's resolution, so the same page lands on different sides of a layout
breakpoint on different machines. A profile here is what one real set-up
gives the page: its width and height in CSS pixels, its pixel ratio, and
whether scrollbars take up page width (Windows) or float over it (Mac).

## Profiles

| Profile | Width | Height | Ratio | Scrollbars | Stands for |
|---|---|---|---|---|---|
| Win-150 | 1280 | 585 | 1.5 | take space | Windows 1080p laptop at 150% |
| Win-125 | 1536 | 730 | 1.25 | take space | Windows 1080p laptop at 125% |
| Mac-13 | 1470 | 826 | 2 | hidden | MacBook Air 13, Pro 14 |
| Mac-16 | 1728 | 987 | 2 | hidden | MacBook Pro 16, Air 15 |
| Ext-1080 | 1920 | 945 | 1 | take space | 1080p monitor |
| Ext-1440 | 2560 | 1323 | 1 | take space | 1440p monitor |
| Ultrawide | 3440 | 1323 | 1 | take space | 21:9 monitor, 3440 x 1440 |
| Half-1440 | 1280 | 1323 | 1 | take space | window snapped to half a 1440p monitor |
| Half-1080 | 960 | 945 | 1 | take space | window snapped to half a 1080p monitor |

Run Win-125, Mac-13 and Ext-1440, plus the docking check below, unless the
hand-over asks for a full sweep, which is all nine. Only Ext-1440's height was
measured on a real screen; the other heights are screen height less an
estimate for the browser's bars, so say so if a result turns on a few pixels
of height.

## Setting a profile

Put this at the top of each `browser_run_code_unsafe` call that sets or reads
a profile. Each call starts with a fresh scope, so the helper has to be
repeated. It keeps its one browser-protocol session on the page object, which
does survive between calls, so that settings never spread across sessions.
Open no other session.

```js
const setProfile = async (W, H, R, hideScrollbars) => {
  await page.setViewportSize({ width: W, height: H });
  const cdp = (page.__appCheckCdp ??= await page.context().newCDPSession(page));
  await cdp.send('Emulation.clearDeviceMetricsOverride');
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: R, mobile: false });
  await cdp.send('Emulation.setScrollbarsHidden', { hidden: hideScrollbars });
};
const readBack = () => page.evaluate(() => {
  const probe = document.createElement('div');
  probe.style.cssText = 'position:absolute;top:-999px;width:100px;height:100px;overflow:scroll';
  document.body.append(probe);
  const scrollbar = probe.offsetWidth - probe.clientWidth;
  probe.remove();
  return {
    w: innerWidth, h: innerHeight, ratio: devicePixelRatio, scrollbar,
    usableWidth: document.documentElement.clientWidth,
    min1024: matchMedia('(min-width: 1024px)').matches,
    min1280: matchMedia('(min-width: 1280px)').matches,
    min1536: matchMedia('(min-width: 1536px)').matches,
  };
});
```

`hideScrollbars` is `true` for the Mac profiles and `false` for the rest.

- After `setProfile`, load or reload the page before measuring, because the
  scrollbar setting applies to documents loaded after it. The docking check is
  the one exception.
- `readBack` must return the profile's width, height and ratio, with scrollbar
  15 where they take space and 0 where hidden. If it does not, report that
  profile as not run and give the numbers you got; a measurement at the wrong
  size proves nothing.
- A breakpoint counts the scrollbar, so it can match while the usable width is
  narrower: at Win-125 the 1536 breakpoint matches with 1521 pixels usable.
  That is the tightest case these profiles exist to catch, so measure against
  the usable width, not the page width.
- A screenshot, and the `browser_resize` tool, drop the ratio to 1. Call
  `setProfile` again after either before you measure anything else. Snapshot,
  find, click, hover, key presses, console and network tools leave the profile
  alone.

## What to measure

For the page and the elements the hand-over names, at each profile, measure
and report numbers. A profile passes on numbers, not on how a screenshot
looks.

- Sideways overflow: `document.documentElement.scrollWidth` minus
  `clientWidth`. Expected 0.
- Each named element inside the page: its box's left at or after 0 and its
  right at or before the usable width. Where it sits in a scrolling pane,
  inside that pane.
- Overlap: the intersection area between named elements that should not
  overlap. Expected 0.
- Cut-off text: an element whose `scrollWidth` is larger than its
  `clientWidth` when the design does not intend truncation.
- Panes sized from the page height: the pane's bottom at or before the page
  height, and its own scroll working when its content is longer.
- Anything the hand-over states as the expected result at a given profile.

## The docking check

This checks what happens when a window moves between a laptop screen and a
monitor while the page stays open.

1. Load the page at Win-125 and measure. The Win-125 measurement you already
   took counts, if nothing has changed on the page since.
2. Call `setProfile` for Ext-1440 without reloading, and measure.
3. Reload at Ext-1440 and measure again. Steps 2 and 3 must give the same
   numbers; a difference means something sized itself once and did not
   recalculate.
4. Call `setProfile` for Win-125 without reloading and measure. It must match
   step 1.

## Screenshots

Take one only where a condition is about how something looks, and take it
last for that profile:
`await page.locator(selector).screenshot({ path: '/tmp/app-check-browser/<profile>-<name>.png' })`.
The image comes out in CSS pixels at ratio 1, at the profile's page size.
Read it once.

## Reporting

One row per profile and measurement: profile, the read-back, what you
measured, the value, the expected value, pass or fail. Give the code you used
for the measurements once, so the result can be re-run. List any profile you
did not run and why.

## What these profiles cannot show

- How Windows draws text, which can shift wrapping by a pixel or two.
- Safari, which uses a different engine from this browser.
- A scrollbar width other than 15 pixels.
