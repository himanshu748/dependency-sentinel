const { chromium } = require("../frontend/node_modules/playwright");
const path = require("node:path");
(async () => {
 const directory = process.argv[2] || path.resolve(__dirname,"../docs");
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({viewport:{width:1440,height:960},deviceScaleFactor:1});
 await page.goto("file://" + path.join(directory,"architecture.svg"));
 await page.screenshot({path:path.join(directory,"architecture.png")});
 await browser.close();
})();
