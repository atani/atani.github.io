async (page) => {
  const formPage = page.context().pages().find((candidate) =>
    candidate.url().includes("docs.google.com/forms/d/1bDsJyzsDi8acjK9ru_N2e5OsIcOIZnMHzDTGrRCxCiA/edit")
  );
  if (!formPage) throw new Error("Target Google Form tab was not found");

  await formPage.bringToFront();

  const geminiDialog = formPage.getByRole("dialog");
  if (await geminiDialog.isVisible().catch(() => false)) {
    const closeButton = geminiDialog.locator("button").last();
    await closeButton.click();
  }

  async function replaceContentEditable(ariaLabel, text) {
    const field = formPage.locator(
      `[contenteditable="true"][aria-label="${ariaLabel}"]`
    ).first();
    await field.waitFor({ state: "visible" });
    await field.evaluate((element) => {
      element.focus();
      element.click();
    });
    for (let i = 0; i < 300; i += 1) await formPage.keyboard.press("Backspace");
    for (let i = 0; i < 300; i += 1) await formPage.keyboard.press("Delete");
    await formPage.keyboard.type(text);
  }

  await replaceContentEditable(
    "フォームのタイトル",
    "アンクラスPort Android版 テスター募集"
  );
  await replaceContentEditable(
    "フォームの説明",
    "Google Playのテスト参加にはGoogleアカウントが必要です。Googleアカウントでお使いのメールアドレスをご記入ください。"
  );
  await replaceContentEditable("質問", "お名前またはハンドルネーム");

  await formPage.getByRole("listbox", { name: "質問の種類" }).click();
  await formPage.getByRole("option", { name: "記述式（短文）" }).click();

  const required = formPage.getByRole("checkbox", { name: "必須" });
  if (await required.isChecked()) await required.click();

  await formPage.waitForTimeout(2500);
  return {
    url: formPage.url(),
    title: await formPage
      .locator('[contenteditable="true"][aria-label="フォームのタイトル"]')
      .first()
      .innerText(),
    description: await formPage
      .locator('[contenteditable="true"][aria-label="フォームの説明"]')
      .first()
      .innerText(),
    question: await formPage
      .locator('[contenteditable="true"][aria-label="質問"]')
      .first()
      .innerText(),
    questionType: await formPage
      .getByRole("listbox", { name: "質問の種類" })
      .innerText(),
    required: await required.isChecked(),
  };
}
