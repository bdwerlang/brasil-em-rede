"""Pandera schemas for Transparencia (Portal da Transparencia) pipeline.

Validates the three entity lists produced by TransparenciaPipeline.transform():
- contracts: Contract nodes (contract_id, object, value, contracting_org, date, cnpj, razao_social)
- offices: PublicOffice nodes (office_id, servidor_id, cpf_partial, name, org, salary)
- amendments: Amendment nodes (amendment_id, author_key, name, object, value)

Column definitions derived from transparencia.py transform() output dictionaries.
"""

import pandera.pandas as pa

# ------------------------------------------------------------------
# Contracts (Contract nodes + Company VENCEU relationship)
# Output keys: contract_id, object, value, contracting_org, date, cnpj, razao_social
# ------------------------------------------------------------------
contracts_schema = pa.DataFrameSchema(
    columns={
        "contract_id": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="contract_id must not be empty"),
        ]),
        "object": pa.Column(str, nullable=True, coerce=True),
        "value": pa.Column(float, nullable=True, coerce=True, checks=[
            pa.Check.ge(0, error="value must be >= 0"),
        ]),
        "contracting_org": pa.Column(str, nullable=True, coerce=True),
        "date": pa.Column(str, nullable=True, coerce=True),
        "cnpj": pa.Column(
            str,
            nullable=True,
            coerce=True,
            checks=[
                pa.Check.str_matches(
                    r"^([A-Za-z0-9]{2}\.[A-Za-z0-9]{3}\.[A-Za-z0-9]{3}/[A-Za-z0-9]{4}-[0-9]{2}|[A-Za-z0-9]{12}[0-9]{2})$",
                    error="CNPJ must be formatted (XX.XXX.XXX/XXXX-XX) or 14 characters",
                ),
            ],
        ),
        "razao_social": pa.Column(str, nullable=True, coerce=True),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Offices (PublicOffice nodes + Person RECEBEU_SALARIO relationship)
# Output keys: office_id, servidor_id, cpf_partial, name, org, salary
# ------------------------------------------------------------------
offices_schema = pa.DataFrameSchema(
    columns={
        "office_id": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="office_id must not be empty"),
        ]),
        "servidor_id": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="servidor_id must not be empty"),
        ]),
        # cpf_partial: 6 middle digits from LGPD-masked CPF, or None
        "cpf_partial": pa.Column(str, nullable=True, coerce=True),
        "name": pa.Column(str, nullable=True, coerce=True),
        "org": pa.Column(str, nullable=True, coerce=True),
        "salary": pa.Column(float, nullable=True, coerce=True, checks=[
            pa.Check.ge(0, error="salary must be >= 0"),
        ]),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Amendments (Amendment nodes + Person AUTOR_EMENDA relationship)
# Output keys: amendment_id, author_key, name, object, value
# ------------------------------------------------------------------
amendments_schema = pa.DataFrameSchema(
    columns={
        "amendment_id": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="amendment_id must not be empty"),
        ]),
        "author_key": pa.Column(str, nullable=False, coerce=True, checks=[
            pa.Check.str_length(min_value=1, error="author_key must not be empty"),
        ]),
        "name": pa.Column(str, nullable=True, coerce=True),
        "object": pa.Column(str, nullable=True, coerce=True),
        "value": pa.Column(float, nullable=True, coerce=True, checks=[
            pa.Check.ge(0, error="value must be >= 0"),
        ]),
    },
    coerce=True,
    strict=False,
)
