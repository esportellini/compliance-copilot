import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const appUrl = "http://localhost:3000";
const apiUrl = "http://localhost:8000/api";
const password = "Compliance123!";
const output = resolve(process.cwd(), "../captures");
await mkdir(output, { recursive: true });

async function token(email) {
  const response = await fetch(`${apiUrl}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
  if (!response.ok) throw new Error(`Login failed: ${response.status}`);
  return (await response.json()).access_token;
}
async function api(accessToken, path, method = "GET", body) {
  const response = await fetch(`${apiUrl}${path}`, { method, headers: { Authorization: `Bearer ${accessToken}`, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) throw new Error(`${method} ${path}: ${response.status} ${await response.text()}`);
  return response.status === 204 ? null : response.json();
}
async function login(page, email) {
  await page.goto(`${appUrl}/login`);
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await Promise.all([page.waitForURL("**/dashboard"), page.getByRole("button", { name: "Entrar" }).click()]);
  await page.waitForLoadState("networkidle");
}
async function shot(page, name) { await page.screenshot({ path: resolve(output, name), animations: "disabled" }); }

const adminToken = await token("admin@demo.local");
const complianceToken = await token("compliance@demo.local");
const employeeToken = await token("colaborador@demo.local");
const products = await api(employeeToken, "/products");
const stock = products.find(item => item.identifier === "XPTO3");

const rules = await api(complianceToken, "/rules");
const stockRule = rules.find(item => item.rule_key === "personal-stock-trading" && item.status === "ACTIVE");
await api(complianceToken, `/rules/${stockRule.id}`, "PATCH", { description: "Toda operação pessoal com ações requer pré-aprovação e registro." });

await api(adminToken, "/settings/pre_approval_sla_hours?value=1", "PUT");
const query = await api(employeeToken, "/copilot/query", "POST", { question: "Posso comprar XPTO3 no valor de R$ 20.000?", product_id: stock.id, amount: 20000, objective: "Diversificação da carteira pessoal" });
const request = await api(employeeToken, "/pre-approvals", "POST", { source_query_id: query.query_id, operation_type: "COMPRA" });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const page = await context.newPage();

await login(page, "compliance@demo.local");
await page.goto(`${appUrl}/rules`);
await page.getByText("v2 · ACTIVE", { exact: true }).waitFor();
await shot(page, "rule-version-history.png");

await page.goto(`${appUrl}/products`);
await page.locator('input[type="file"]').setInputFiles({ name: "restricted-list.csv", mimeType: "text/csv", buffer: Buffer.from("identifier,name,reason,active\nACME3,ACME S.A.,Conflito interno,true\nXYZ4,XYZ Holdings,Under review,true\n") });
await page.getByText("UPDATE", { exact: true }).waitFor();
await shot(page, "restricted-list-import.png");

await page.goto(`${appUrl}/pre-approvals`);
await page.getByRole("cell", { name: "Vence em breve" }).waitFor();
await shot(page, "approval-queue.png");

await api(complianceToken, `/pre-approvals/${request.id}/status`, "PATCH", { status: "IN_REVIEW" });
await api(complianceToken, `/pre-approvals/${request.id}/comments`, "POST", { body: "Documentação e limite conferidos conforme a política vigente." });
await api(complianceToken, `/pre-approvals/${request.id}/status`, "PATCH", { status: "APPROVED_WITH_CONDITIONS", compliance_opinion: "Aprovada com limite de R$ 20.000 e reporte no mesmo dia." });
await page.goto(`${appUrl}/pre-approvals/${request.id}`);
await page.getByText("Aprovado c/ ressalvas", { exact: true }).waitFor();
await shot(page, "audit-package.png");

const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const mobilePage = await mobile.newPage();
const checks = [];
for (const [email, path] of [["colaborador@demo.local", "/dashboard"], ["compliance@demo.local", "/rules"], ["auditor@demo.local", `/pre-approvals/${request.id}`], ["admin@demo.local", "/products"]]) {
  await login(mobilePage, email);
  await mobilePage.goto(`${appUrl}${path}`); await mobilePage.waitForLoadState("networkidle");
  checks.push(await mobilePage.evaluate(() => ({ path: location.pathname, width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, noGlobalOverflow: document.documentElement.scrollWidth <= document.documentElement.clientWidth })));
}
await writeFile(resolve(output, "mobile-smoke.json"), JSON.stringify({ viewport: "390x844", checks }, null, 2));
await mobile.close(); await context.close(); await browser.close();
