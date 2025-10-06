CREATE TABLE t_nse_fii_dii_eq_data (
  run_dt   date PRIMARY KEY,
  dii_buy  numeric(9,2),
  dii_sell numeric(9,2),
  dii_net  numeric(7,2),
  fii_buy  numeric(9,2),
  fii_sell numeric(9,2),
  fii_net  numeric(7,2),
  iu_ts    timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
