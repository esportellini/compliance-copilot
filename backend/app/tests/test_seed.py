"""The demo seed must produce the documented scenarios and own its demo data."""
from app.models.document import DocumentChunk, PolicyDocument
from app.models.product import FinancialProduct
from app.models.restricted import RestrictedListItem
from app.models.rule import ComplianceRule
from app.models.setting import SystemSetting
from app.models.training import TrainingItem
from app.models.user import User
from app.seed import seed
from app.services.copilot import CopilotInput, run_query


def test_seeded_policy_supports_all_demo_decisions(db):
    seed(db)
    user = db.query(User).filter(User.email == "colaborador@demo.local").one()
    open_fund = (
        db.query(FinancialProduct)
        .filter(FinancialProduct.identifier == "FMALT")
        .one()
    )
    normal_stock = (
        db.query(FinancialProduct)
        .filter(FinancialProduct.identifier == "XPTO3")
        .one()
    )
    restricted_stock = (
        db.query(FinancialProduct)
        .filter(FinancialProduct.identifier == "ACME3")
        .one()
    )

    cases = [
        (
            CopilotInput(
                user_id=user.id,
                question="Posso investir neste fundo aberto?",
                product_id=open_fund.id,
                amount=100_000,
            ),
            "ALLOWED",
        ),
        (
            CopilotInput(
                user_id=user.id,
                question="Posso investir neste fundo aberto?",
                product_id=open_fund.id,
                amount=100_000.01,
            ),
            "REPORT_REQUIRED",
        ),
        (
            CopilotInput(
                user_id=user.id,
                question="Posso comprar estas ações?",
                product_id=normal_stock.id,
            ),
            "PRE_APPROVAL_REQUIRED",
        ),
        (
            CopilotInput(
                user_id=user.id,
                question="Posso comprar estas ações?",
                product_id=restricted_stock.id,
            ),
            "RESTRICTED",
        ),
        (
            CopilotInput(
                user_id=user.id,
                question="Posso comprar um criptoativo?",
                product_type="CRYPTO",
            ),
            "RESTRICTED",
        ),
        (
            CopilotInput(
                user_id=user.id,
                question="Posso operar este produto sem política?",
                product_type="OTHER",
            ),
            "INCONCLUSIVE",
        ),
    ]

    results = [(run_query(query, db), expected) for query, expected in cases]

    observed = [result.decision for result, _ in results]
    expected = [expected for _, expected in results]
    assert observed == expected, [
        (result.decision, result.justification, result.matched_rules)
        for result, _ in results
    ]
    restricted_result = results[3][0]
    assert restricted_result.matched_rules == ["restricted_list"]
    assert restricted_result.requires_human_review is False


def test_seed_is_idempotent_and_refreshes_owned_demo_records(db):
    seed(db)

    interpretation = db.query(TrainingItem).filter(
        TrainingItem.title == "Como interpretar as decisões"
    ).one()
    human_review = db.query(TrainingItem).filter(
        TrainingItem.title == "Quando solicitar revisão humana"
    ).one()
    interpretation.body = "REQUER REPORTE: execute e registre no mesmo dia."
    human_review.body = "Risco alto sempre exige revisão humana."
    obsolete_setting = db.query(SystemSetting).filter(
        SystemSetting.key == "restricted_list_active"
    ).one_or_none()
    if obsolete_setting:
        obsolete_setting.value = "false"
    else:
        db.add(
            SystemSetting(
                key="restricted_list_active",
                value="false",
                description="Configuração antiga sem consumidor",
            )
        )
    db.commit()

    seed(db)
    counts_after_upgrade = {
        "users": db.query(User).count(),
        "products": db.query(FinancialProduct).count(),
        "restricted": db.query(RestrictedListItem).count(),
        "rules": db.query(ComplianceRule).count(),
        "documents": db.query(PolicyDocument).count(),
        "chunks": db.query(DocumentChunk).count(),
        "training": db.query(TrainingItem).count(),
        "settings": db.query(SystemSetting).count(),
    }
    seed(db)
    counts_after_rerun = {
        "users": db.query(User).count(),
        "products": db.query(FinancialProduct).count(),
        "restricted": db.query(RestrictedListItem).count(),
        "rules": db.query(ComplianceRule).count(),
        "documents": db.query(PolicyDocument).count(),
        "chunks": db.query(DocumentChunk).count(),
        "training": db.query(TrainingItem).count(),
        "settings": db.query(SystemSetting).count(),
    }

    assert counts_after_rerun == counts_after_upgrade
    assert "antes de executar" in interpretation.body
    assert "INCONCLUSIVO ou REQUER PRÉ-APROVAÇÃO" in human_review.body
    assert db.query(SystemSetting).all()[0].key == "data_retention_days"
