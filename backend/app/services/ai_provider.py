"""AI provider abstraction.

Dois modos:
  mock   — offline, determinístico, respostas contextuais por decisão/tipo
  openai — wrapper fino sobre openai SDK; ativado via AI_PROVIDER=openai + OPENAI_API_KEY

O mock é sofisticado o suficiente para desenvolvimento: varia a justificativa
com base na decisão e no tipo de produto, sem depender de nenhuma API externa.
"""
from __future__ import annotations

import hashlib
import math
import re


class AIProvider:
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def answer(self, system: str, user: str) -> str:
        raise NotImplementedError


class MockAIProvider(AIProvider):
    """Provider offline determinístico.

    Os embeddings são gerados por hash SHA-256 normalizado.
    As justificativas variam com base em palavras-chave da decisão e do
    tipo de produto extraídas do prompt — suficiente para demos e testes.
    """

    DIM = 256

    def embed(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(self.DIM):
            byte_val = seed[i % len(seed)]
            vec.append((byte_val / 255.0) * 2 - 1)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def answer(self, system: str, user: str) -> str:  # noqa: ARG002
        combined = user.lower()

        # detectar tipo de produto
        product_hints = {
            "crypto": "criptoativos",
            "cripto": "criptoativos",
            "derivative": "derivativos",
            "derivativo": "derivativos",
            "stock": "ações individuais",
            "ação": "ações individuais",
            "ações": "ações individuais",
            "fundo fechado": "fundos fechados",
            "closed_fund": "fundos fechados",
            "open_fund": "fundos abertos",
            "fundo aberto": "fundos abertos",
            "fixed_income": "renda fixa",
            "renda fixa": "renda fixa",
            "ipo": "IPOs e ofertas públicas",
        }
        produto = "este tipo de ativo"
        for key, label in product_hints.items():
            if key in combined:
                produto = label
                break

        # detectar decisão no prompt
        if "restricted" in combined or "restrito" in combined or "blocked" in combined:
            return (
                f"A política interna veda operações com {produto} para colaboradores da firma. "
                "Esta restrição é determinada por regra estruturada de compliance e não admite exceções "
                "sem aprovação formal do Comitê de Compliance. "
                "Nenhuma operação deve ser iniciada enquanto esta condição persistir."
            )
        if "pre_approval" in combined or "pré-aprovação" in combined or "pre-approval" in combined:
            return (
                f"Operações com {produto} estão sujeitas a aprovação prévia do compliance "
                "antes de qualquer execução. "
                "Submeta a solicitação de pré-aprovação com o ativo, valor estimado e justificativa de negócio. "
                "A equipe de compliance responderá em até 48 horas úteis."
            )
        if "report_required" in combined or "reporte" in combined or "reportar" in combined:
            return (
                f"A operação com {produto} é permitida, porém deve ser reportada "
                "ao sistema de controles internos no mesmo dia da execução. "
                "Mantenha o registro da operação acessível para eventuais revisões de auditoria. "
                "O não reporte configura infração à política de compliance."
            )
        if "allowed" in combined or "permitido" in combined:
            return (
                f"A operação com {produto} está de acordo com as diretrizes de compliance vigentes. "
                "Verifique os limites de concentração aplicáveis ao seu perfil antes de executar. "
                "Mantenha o registro da operação para fins de auditoria interna."
            )
        if "inconclusive" in combined or "inconclusivo" in combined:
            return (
                f"Não foi possível determinar automaticamente a conformidade da operação com {produto}. "
                "A ausência de regra específica ou a presença de condições conflitantes requer avaliação "
                "direta da equipe de compliance. "
                "Não execute a operação sem orientação formal."
            )
        # fallback genérico
        return (
            "Com base nas políticas internas e nas regras de compliance vigentes, "
            "a análise estruturada determinou a decisão indicada. "
            "Consulte os documentos de referência listados para os critérios completos aplicados. "
            "Em caso de dúvida, entre em contato com a equipe de compliance antes de prosseguir."
        )


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            input=text[:8000], model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def answer(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=600,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""


_instance: AIProvider | None = None


def get_provider() -> AIProvider:
    global _instance
    if _instance is None:
        from app.core.config import settings
        if settings.ai_provider == "openai" and settings.openai_api_key:
            _instance = OpenAIProvider(settings.openai_api_key, settings.openai_model)
        else:
            _instance = MockAIProvider()
    return _instance
