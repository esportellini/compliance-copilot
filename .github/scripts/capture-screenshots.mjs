import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const appUrl = "http://localhost:3000";
const apiUrl = "http://localhost:8000/api";
const password = "Compliance123!";
const output = resolve(process.cwd(), "../captures");

await mkdir(output, { recursive: true });

async function token(email) {
  const response = await fetch(`${apiUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(`Login failed for ${email}: ${response.status}`);
  return (await response.json()).access_token;
}

async function api(accessToken, path, method = "GET", body) {
  const response = await fetch(`${apiUrl}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(`${method} ${path}: ${response.status} ${await response.text()}`);
  return response.status === 204 ? null : response.json();
}

async function login(page, email) {
  await page.goto(`${appUrl}/login`);
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: "Entrar" }).click(),
  ]);
  await page.waitForLoadState("networkidle");
}

async function screenshot(page, name) {
  await page.screenshot({ path: resolve(output, name), animations: "disabled" });
}

const employeeToken = await token("colaborador@demo.local");
const products = await api(employeeToken, "/products");
const product = (identifier) => products.find((item) => item.identifier === identifier);

for (const query of [
  { question: "Posso aplicar R$ 50.000 no Fundo Multimercado Alpha?", product_id: product("FMALT").id, product_type: "OPEN_FUND", amount: 50000 },
  { question: "Posso aplicar R$ 150.000 no Fundo Multimercado Alpha?", product_id: product("FMALT").id, product_type: "OPEN_FUND", amount: 150000 },
  { question: "Posso comprar ACME3?", product_id: product("ACME3").id, product_type: "STOCK", amount: 10000 },
  { question: "Posso comprar CriptoNova?", product_id: product("CNOVA").id, product_type: "CRYPTO", amount: 10000 },
  { question: "Posso comprar a Debênture Ômega 2028?", product_id: product("OMGDB28").id, product_type: "FIXED_INCOME", amount: 10000 },
]) await api(employeeToken, "/copilot/query", "POST", query);

const browser = await chromium.launch({ headless: true });
const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const page = await desktop.newPage();

await login(page, "colaborador@demo.local");
await page.goto(`${appUrl}/copilot`);
await page.getByRole("button", { name: "Adicionar contexto estruturado" }).click();
await page.getByLabel(/Pergunta sobre a operação/).fill("Posso comprar ações da XPTO3 no valor de R$ 20.000?");
await page.getByLabel("Tipo de produto").selectOption("STOCK");
await page.getByLabel("Produto ou ticker").fill("XPTO3");
await page.getByLabel("Valor estimado").fill("20000");
await page.getByLabel("Objetivo").fill("Diversificação da carteira pessoal");
await page.getByRole("button", { name: "Analisar operação" }).click();
const result = page.locator('[aria-label="Resultado da análise"]');
await result.waitFor();
await page.getByText("Requer Pré-aprovação", { exact: true }).waitFor();
await result.evaluate((element) => window.scrollTo(0, element.getBoundingClientRect().top + window.scrollY - 82));
await screenshot(page, "copilot-pre-approval.png");

await page.getByRole("heading", { name: "Evidências documentais" }).evaluate(
  (element) => window.scrollTo(0, element.getBoundingClientRect().top + window.scrollY - 480),
);
await screenshot(page, "copilot-evidence.png");

const sourceQuery = (await api(employeeToken, "/copilot/history"))[0];
const request = await api(employeeToken, "/pre-approvals", "POST", {
  source_query_id: sourceQuery.id,
  product_id: sourceQuery.product_id,
  product_label: sourceQuery.product_label ?? sourceQuery.product_identifier,
  operation_type: "COMPRA",
  estimated_amount: sourceQuery.amount,
  justification: sourceQuery.objective,
});
const requestId = request.id;
const complianceToken = await token("compliance@demo.local");
await api(complianceToken, `/pre-approvals/${requestId}/comments`, "POST", {
  body: "Documentação e limites conferidos conforme a política vigente.",
});
await api(complianceToken, `/pre-approvals/${requestId}/status`, "PATCH", { status: "IN_REVIEW" });
await api(complianceToken, `/pre-approvals/${requestId}/status`, "PATCH", {
  status: "APPROVED_WITH_CONDITIONS",
  compliance_opinion: "Aprovada com limite de R$ 20.000 e reporte da execução no mesmo dia.",
});

await login(page, "compliance@demo.local");
await page.goto(`${appUrl}/pre-approvals/${requestId}`);
await page.getByText("Aprovado c/ ressalvas", { exact: true }).waitFor();
await page.evaluate(() => window.scrollTo(0, 0));
await screenshot(page, "pre-approval-detail.png");

await login(page, "compliance@demo.local");
await page.goto(`${appUrl}/dashboard`);
await page.getByRole("heading", { name: "Distribuição das decisões" }).waitFor();
await screenshot(page, "dashboard.png");

await login(page, "auditor@demo.local");
await page.goto(`${appUrl}/audit`);
await page.getByRole("heading", { name: "Trilha de Auditoria" }).waitFor();
await page.getByText("PRE_APPROVAL_DECISION", { exact: true }).first().waitFor();
await screenshot(page, "audit-trail.png");

const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const mobilePage = await mobile.newPage();
await login(mobilePage, "colaborador@demo.local");
const mobileChecks = [];
for (const path of ["/dashboard", "/copilot", `/history/${(await api(employeeToken, "/copilot/history"))[0].id}`, `/pre-approvals/${requestId}`]) {
  await mobilePage.goto(`${appUrl}${path}`);
  await mobilePage.waitForLoadState("networkidle");
  mobileChecks.push(await mobilePage.evaluate(() => ({
    path: location.pathname,
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    noGlobalOverflow: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  })));
}
await mobilePage.goto(`${appUrl}/dashboard`);
await mobilePage.getByRole("button", { name: "Abrir menu" }).click();
const drawerOpened = await mobilePage.getByRole("navigation", { name: "Navegação principal" }).isVisible();
await mobilePage.getByRole("button", { name: "Fechar menu" }).click();
const drawerClosed = await mobilePage.getByRole("button", { name: "Abrir menu" }).isVisible();
await writeFile(resolve(output, "mobile-smoke.json"), JSON.stringify({ viewport: "390x844", drawerOpened, drawerClosed, pages: mobileChecks }, null, 2));

await mobile.close();
await desktop.close();
await browser.close();
