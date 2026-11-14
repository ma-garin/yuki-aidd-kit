async (page, assets) => {
  const items = assets.items;
  const evidence = [];
  for (const width of [1366, 360]) {
    await page.setViewportSize({width, height: 660});
    await page.setContent('<link rel="stylesheet"><main><button id="trigger">実行</button><div id="results"></div></main>');
    await page.addStyleTag({content: assets.css});
    await page.addStyleTag({content:'*, *::before, *::after {box-sizing:border-box}'});
    await page.addScriptTag({content: assets.js});
    for (const item of items) {
      if (item.id === 'confirm') {
        for (const action of ['.confirm-cancel', '.confirm-ok', 'Escape']) {
          await page.evaluate(example => { window.confirmation = (new Function('return (async () => {' + example + '; return confirmed; })()'))(); }, item.example);
          const box = await page.locator('dialog').boundingBox();
          if (!box || box.x < 0 || box.x + box.width > width + 1 || box.y + box.height > 660) throw Error('dialog not reachable');
          if (action === 'Escape') await page.keyboard.press('Escape'); else await page.locator(action).click();
          const result = await page.evaluate(() => window.confirmation);
          if (result !== (action === '.confirm-ok')) throw Error('wrong confirm result');
        }
      } else if (item.id === 'busy') {
        await page.evaluate(() => { window.finishBusy = Feedback.busy('読み込んでいます'); });
        if (!(await page.locator('.toast-busy').isVisible())) throw Error('busy missing');
        await page.evaluate(() => window.finishBusy({ok:'読み込みました'}));
        await page.locator('.toast-busy').waitFor({state:'detached'});
        await page.evaluate(example => (new Function(example))(), item.example);
      } else {
        await page.evaluate(example => (new Function(example))(), item.example);
        if (item.id === 'success' && !(await page.locator('.toast-ok').first().isVisible())) throw Error('success missing');
        if (item.id === 'error') {
          await page.getByText('再試行', {exact:true}).click();
          if (!(await page.evaluate(() => window.retryRequested))) throw Error('retry missing');
        }
        if (item.id === 'empty') {
          await page.getByText('条件を変更', {exact:true}).click();
          if (!(await page.evaluate(() => window.editRequested))) throw Error('edit missing');
        }
      }
      evidence.push({width, id:item.id, status:'PASS'});
    }
  }
  return {specified:10, checked:evidence.length, evidence};
}
