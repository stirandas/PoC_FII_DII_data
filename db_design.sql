CREATE TABLE t_nse_fii_dii_eq_data (
  run_dt   date PRIMARY KEY,
  dii_buy  numeric(9,2) NOT NULL,
  dii_sell numeric(9,2) NOT NULL,
  dii_net  numeric(7,2) NOT NULL,
  fii_buy  numeric(9,2) NOT NULL,
  fii_sell numeric(9,2) NOT NULL,
  fii_net  numeric(7,2) NOT NULL,
  i_ts    timestamptz,
  u_ts    timestamptz
);
