CREATE TABLE IF NOT EXISTS foods (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  name_en TEXT,
  name_original TEXT,
  name_zh TEXT,
  source_country TEXT NOT NULL,
  source_id TEXT,
  category TEXT,
  kcal_100g REAL,
  protein_g REAL,
  fat_g REAL,
  carbs_g REAL,
  sodium_mg REAL,
  calcium_mg REAL,
  iron_mg REAL,
  zinc_mg REAL,
  selenium_ug REAL,
  vitamin_a_ug REAL,
  vitamin_c_mg REAL,
  vitamin_d_ug REAL,
  vitamin_e_mg REAL,
  vitamin_b1_mg REAL,
  vitamin_b2_mg REAL,
  vitamin_b3_mg REAL,
  serving_ref TEXT,
  image_path TEXT,
  raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_foods_name ON foods(name);
CREATE INDEX IF NOT EXISTS idx_foods_country ON foods(source_country);
CREATE INDEX IF NOT EXISTS idx_foods_kcal ON foods(kcal_100g);
