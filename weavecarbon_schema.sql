-- =============================================
-- WEAVECARBON COMPLETE DATABASE SCHEMA
-- PostgreSQL Script - Updated 2026-02-09
-- Standalone PostgreSQL (No Supabase Auth dependency)
-- Total: 29 Tables (B2B + B2C modules)
-- =============================================

-- =============================================
-- 1. ENUMS (14 types)
-- =============================================

-- User & Business
CREATE TYPE public.app_role AS ENUM ('b2b', 'b2c', 'admin');
CREATE TYPE public.business_type AS ENUM ('shop_online', 'brand', 'factory');
CREATE TYPE public.pricing_plan AS ENUM ('starter', 'standard', 'export');

-- Company Member Roles (B2B internal team management)
CREATE TYPE public.company_role AS ENUM ('admin', 'member', 'viewer');
CREATE TYPE public.member_status AS ENUM ('active', 'invited', 'disabled');

-- Products & Logistics
CREATE TYPE public.product_status AS ENUM ('draft', 'active', 'archived');
CREATE TYPE public.transport_mode AS ENUM ('road', 'sea', 'air', 'rail');
CREATE TYPE public.shipment_status AS ENUM ('pending', 'in_transit', 'delivered', 'cancelled');

-- Reports & Compliance
CREATE TYPE public.report_type AS ENUM ('carbon_audit', 'compliance', 'export_declaration', 'sustainability');
CREATE TYPE public.report_status AS ENUM ('draft', 'generated', 'approved', 'exported');
CREATE TYPE public.market_status AS ENUM ('good', 'warning', 'danger');
CREATE TYPE public.impact_level AS ENUM ('high', 'medium', 'low');

-- B2C Donation
CREATE TYPE public.donation_category AS ENUM ('charity', 'recycle');
CREATE TYPE public.delivery_method AS ENUM ('drop_off', 'pickup', 'shipping');
CREATE TYPE public.donation_status AS ENUM ('pending', 'scheduled', 'in_transit', 'received', 'processed', 'completed');


-- =============================================
-- 2. USERS TABLE (Standalone Authentication)
-- =============================================

CREATE TABLE public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,              -- bcrypt hashed password
  full_name TEXT,
  avatar_url TEXT,
  email_verified BOOLEAN NOT NULL DEFAULT false,
  email_verified_at TIMESTAMPTZ,
  failed_login_attempts INTEGER NOT NULL DEFAULT 0,
  locked_until TIMESTAMPTZ,                 -- Account lockout timestamp
  last_login_at TIMESTAMPTZ,
  is_demo_user BOOLEAN NOT NULL DEFAULT false,
  demo_expires_at TIMESTAMPTZ,              -- For demo account cleanup
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast email lookup
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_demo ON public.users(is_demo_user) WHERE is_demo_user = true;


-- =============================================
-- 3. EMAIL VERIFICATION TOKENS
-- =============================================

CREATE TABLE public.email_verification_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,          -- SHA256 hash of token
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_email_tokens_user ON public.email_verification_tokens(user_id);
CREATE INDEX idx_email_tokens_expires ON public.email_verification_tokens(expires_at);


-- =============================================
-- 4. REFRESH TOKENS (JWT Token Rotation)
-- =============================================

CREATE TABLE public.refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,          -- SHA256 hash of refresh token
  expires_at TIMESTAMPTZ NOT NULL,
  is_revoked BOOLEAN NOT NULL DEFAULT false,
  revoked_at TIMESTAMPTZ,
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_refresh_tokens_user ON public.refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON public.refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires ON public.refresh_tokens(expires_at);


-- =============================================
-- 5. CORE IDENTITY TABLES
-- =============================================

-- Companies table (B2B organizations)
CREATE TABLE public.companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  business_type business_type NOT NULL,
  current_plan pricing_plan NOT NULL DEFAULT 'starter',
  target_markets TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Profiles table (Extended user info, linked to public.users)
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
  email TEXT,
  full_name TEXT,
  avatar_url TEXT,
  company_id UUID REFERENCES public.companies(id) ON DELETE SET NULL,
  is_demo_user BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_profiles_user ON public.profiles(user_id);
CREATE INDEX idx_profiles_company ON public.profiles(company_id);

-- User roles table (Role-based access control)
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role app_role NOT NULL DEFAULT 'b2c',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, role)
);

CREATE INDEX idx_user_roles_user ON public.user_roles(user_id);


-- =============================================
-- 5.1 COMPANY_MEMBERS (B2B team management)
-- Root Admin creates Member/Viewer accounts within same company
-- =============================================

CREATE TABLE public.company_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role company_role NOT NULL DEFAULT 'member',
  status member_status NOT NULL DEFAULT 'invited',
  invited_by UUID REFERENCES public.users(id),
  last_login TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(company_id, user_id)
);

CREATE INDEX idx_company_members_company ON public.company_members(company_id);
CREATE INDEX idx_company_members_user ON public.company_members(user_id);
CREATE INDEX idx_company_members_status ON public.company_members(status);


-- =============================================
-- 6. CHAT TABLES
-- =============================================

CREATE TABLE public.chat_conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  session_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES public.chat_conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 7. EMISSION FACTORS (Reference table)
-- =============================================

CREATE TABLE public.emission_factors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category TEXT NOT NULL,
  subcategory TEXT NOT NULL,
  factor_value NUMERIC(12, 6) NOT NULL,
  unit TEXT NOT NULL,
  source TEXT,
  version TEXT NOT NULL DEFAULT '2024',
  valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
  valid_to DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 8. SUPPLIERS (B2B supply chain)
-- =============================================

CREATE TABLE public.suppliers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  country TEXT NOT NULL,
  sustainability_score NUMERIC(3, 1) CHECK (sustainability_score >= 0 AND sustainability_score <= 10),
  certifications TEXT[],
  contact_email TEXT,
  contact_phone TEXT,
  address TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 9. MATERIALS (Fabric & packaging library)
-- =============================================

CREATE TABLE public.materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  emission_factor_id UUID REFERENCES public.emission_factors(id),
  default_co2e_per_kg NUMERIC(10, 4) NOT NULL,
  is_recycled BOOLEAN DEFAULT false,
  recycled_content_percentage NUMERIC(5, 2) DEFAULT 0,
  certifications TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 10. PRODUCTS (B2B product catalog)
-- =============================================

CREATE TABLE public.products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  sku TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  category TEXT,
  weight_kg NUMERIC(10, 4),
  status product_status NOT NULL DEFAULT 'draft',
  total_co2e NUMERIC(12, 4),
  materials_co2e NUMERIC(12, 4),
  production_co2e NUMERIC(12, 4),
  transport_co2e NUMERIC(12, 4),
  packaging_co2e NUMERIC(12, 4),
  data_confidence_score NUMERIC(5, 2) DEFAULT 0,
  image_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(company_id, sku)
);


-- =============================================
-- 11. PRODUCT_MATERIALS (Junction: Product ↔ Material)
-- =============================================

CREATE TABLE public.product_materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  material_id UUID NOT NULL REFERENCES public.materials(id) ON DELETE RESTRICT,
  supplier_id UUID REFERENCES public.suppliers(id),
  percentage NUMERIC(5, 2) NOT NULL CHECK (percentage > 0 AND percentage <= 100),
  weight_kg NUMERIC(10, 4),
  co2e_contribution NUMERIC(12, 4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 12. SHIPMENTS (B2B logistics)
-- =============================================

CREATE TABLE public.shipments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  reference_number TEXT,
  origin_country TEXT NOT NULL,
  origin_city TEXT,
  origin_address TEXT,
  origin_lat NUMERIC(10, 7),
  origin_lng NUMERIC(10, 7),
  destination_country TEXT NOT NULL,
  destination_city TEXT,
  destination_address TEXT,
  destination_lat NUMERIC(10, 7),
  destination_lng NUMERIC(10, 7),
  status shipment_status NOT NULL DEFAULT 'pending',
  total_weight_kg NUMERIC(12, 4),
  total_distance_km NUMERIC(12, 2),
  total_co2e NUMERIC(12, 4),
  estimated_arrival DATE,
  actual_arrival DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 13. SHIPMENT_LEGS (Multi-leg transport)
-- =============================================

CREATE TABLE public.shipment_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id UUID NOT NULL REFERENCES public.shipments(id) ON DELETE CASCADE,
  leg_order INTEGER NOT NULL,
  transport_mode transport_mode NOT NULL,
  origin_location TEXT NOT NULL,
  destination_location TEXT NOT NULL,
  distance_km NUMERIC(12, 2),
  duration_hours NUMERIC(8, 2),
  co2e NUMERIC(12, 4),
  emission_factor_used NUMERIC(12, 6),
  carrier_name TEXT,
  vehicle_type TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 14. SHIPMENT_PRODUCTS (Products in shipment)
-- =============================================

CREATE TABLE public.shipment_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id UUID NOT NULL REFERENCES public.shipments(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL DEFAULT 1,
  weight_kg NUMERIC(10, 4),
  allocated_co2e NUMERIC(12, 4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 15. CARBON_CALCULATIONS (Detailed audit)
-- =============================================

CREATE TABLE public.carbon_calculations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  product_id UUID REFERENCES public.products(id) ON DELETE SET NULL,
  shipment_id UUID REFERENCES public.shipments(id) ON DELETE SET NULL,
  calculation_type TEXT NOT NULL,
  period_start DATE,
  period_end DATE,
  materials_co2e NUMERIC(12, 4) DEFAULT 0,
  production_co2e NUMERIC(12, 4) DEFAULT 0,
  transport_co2e NUMERIC(12, 4) DEFAULT 0,
  packaging_co2e NUMERIC(12, 4) DEFAULT 0,
  total_co2e NUMERIC(12, 4) NOT NULL,
  methodology TEXT,
  emission_factor_version TEXT DEFAULT '2024',
  calculated_by UUID REFERENCES public.users(id),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 16. CARBON_TARGETS (Trend tracking)
-- =============================================

CREATE TABLE public.carbon_targets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  year INTEGER NOT NULL,
  month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
  target_co2e NUMERIC(12, 4) NOT NULL,
  actual_co2e NUMERIC(12, 4),
  reduction_percentage NUMERIC(5, 2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(company_id, year, month)
);


-- =============================================
-- 17. MARKET_READINESS (Export compliance)
-- =============================================

CREATE TABLE public.market_readiness (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  market_code TEXT NOT NULL,
  market_name TEXT NOT NULL,
  readiness_score NUMERIC(5, 2) NOT NULL CHECK (readiness_score >= 0 AND readiness_score <= 100),
  status market_status NOT NULL DEFAULT 'warning',
  requirements_met TEXT[],
  requirements_missing TEXT[],
  last_assessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(company_id, market_code)
);


-- =============================================
-- 18. CERTIFICATES (Sustainability certs)
-- =============================================

CREATE TABLE public.certificates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  product_id UUID REFERENCES public.products(id) ON DELETE SET NULL,
  certificate_type TEXT NOT NULL,
  certificate_number TEXT,
  issuing_body TEXT NOT NULL,
  issue_date DATE NOT NULL,
  expiry_date DATE,
  document_url TEXT,
  is_valid BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 19. REPORTS (Compliance & audit reports)
-- =============================================

CREATE TABLE public.reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  report_type report_type NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  period_start DATE,
  period_end DATE,
  target_market TEXT,
  status report_status NOT NULL DEFAULT 'draft',
  file_url TEXT,
  file_format TEXT,
  generated_by UUID REFERENCES public.users(id),
  approved_by UUID REFERENCES public.users(id),
  approved_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 20. AI_RECOMMENDATIONS (Carbon reduction suggestions)
-- =============================================

CREATE TABLE public.ai_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  product_id UUID REFERENCES public.products(id) ON DELETE SET NULL,
  recommendation_text TEXT NOT NULL,
  impact_level impact_level NOT NULL DEFAULT 'medium',
  estimated_reduction_percentage NUMERIC(5, 2),
  estimated_cost_savings NUMERIC(12, 2),
  category TEXT,
  is_implemented BOOLEAN DEFAULT false,
  implemented_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 21. COLLECTION_POINTS (B2C drop-off locations)
-- =============================================

CREATE TABLE public.collection_points (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  address TEXT NOT NULL,
  city TEXT NOT NULL,
  district TEXT,
  latitude NUMERIC(10, 7),
  longitude NUMERIC(10, 7),
  phone TEXT,
  operating_hours TEXT,
  accepts_charity BOOLEAN DEFAULT true,
  accepts_recycle BOOLEAN DEFAULT true,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 22. MATERIAL_REWARDS (B2C rewards reference)
-- =============================================

CREATE TABLE public.material_rewards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  material_name TEXT NOT NULL,
  material_category TEXT NOT NULL,
  points_per_kg NUMERIC(10, 2) NOT NULL,
  co2_saved_per_kg NUMERIC(10, 4) NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 23. DONATIONS (B2C main donation records)
-- =============================================

CREATE TABLE public.donations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  category donation_category NOT NULL,
  delivery_method delivery_method NOT NULL,
  status donation_status NOT NULL DEFAULT 'pending',
  product_qr_code TEXT,
  item_description TEXT,
  material_id UUID REFERENCES public.material_rewards(id),
  estimated_weight_kg NUMERIC(10, 4),
  actual_weight_kg NUMERIC(10, 4),
  collection_point_id UUID REFERENCES public.collection_points(id),
  pickup_address TEXT,
  pickup_scheduled_at TIMESTAMPTZ,
  shipping_tracking_number TEXT,
  base_points INTEGER DEFAULT 0,
  bonus_points INTEGER DEFAULT 0,
  total_points INTEGER DEFAULT 0,
  co2_saved NUMERIC(12, 4) DEFAULT 0,
  confirmed_at TIMESTAMPTZ,
  confirmation_method TEXT CHECK (confirmation_method IS NULL OR confirmation_method IN ('gps', 'staff')),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 24. DONATION_ITEMS (B2C individual items in donation)
-- =============================================

CREATE TABLE public.donation_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  donation_id UUID NOT NULL REFERENCES public.donations(id) ON DELETE CASCADE,
  item_name TEXT NOT NULL,
  item_type TEXT,
  condition TEXT,
  material_id UUID REFERENCES public.material_rewards(id),
  weight_kg NUMERIC(10, 4),
  points_earned INTEGER DEFAULT 0,
  co2_saved NUMERIC(12, 4) DEFAULT 0,
  image_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 25. PICKUP_BOOKINGS (B2C home pickup logistics)
-- =============================================

CREATE TABLE public.pickup_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  donation_id UUID NOT NULL REFERENCES public.donations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  pickup_address TEXT NOT NULL,
  pickup_city TEXT NOT NULL,
  pickup_district TEXT,
  pickup_phone TEXT NOT NULL,
  preferred_date DATE NOT NULL,
  preferred_time_slot TEXT,
  special_instructions TEXT,
  status TEXT DEFAULT 'scheduled',
  confirmed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 26. USER_REWARDS (B2C accumulated rewards)
-- =============================================

CREATE TABLE public.user_rewards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
  total_points INTEGER DEFAULT 0,
  total_donations INTEGER DEFAULT 0,
  total_items_donated INTEGER DEFAULT 0,
  total_weight_kg NUMERIC(12, 4) DEFAULT 0,
  total_co2_saved NUMERIC(12, 4) DEFAULT 0,
  current_level TEXT DEFAULT 'Beginner',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 27. REWARD_TRANSACTIONS (B2C points history)
-- =============================================

CREATE TABLE public.reward_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  donation_id UUID REFERENCES public.donations(id) ON DELETE SET NULL,
  transaction_type TEXT NOT NULL,
  points INTEGER NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================
-- 28. INDEXES FOR PERFORMANCE
-- =============================================

-- Core identity indexes
CREATE INDEX idx_companies_business_type ON public.companies(business_type);

-- Product indexes
CREATE INDEX idx_products_company ON public.products(company_id);
CREATE INDEX idx_products_status ON public.products(status);
CREATE INDEX idx_product_materials_product ON public.product_materials(product_id);
CREATE INDEX idx_product_materials_material ON public.product_materials(material_id);

-- Shipment indexes
CREATE INDEX idx_shipments_company ON public.shipments(company_id);
CREATE INDEX idx_shipments_status ON public.shipments(status);
CREATE INDEX idx_shipment_legs_shipment ON public.shipment_legs(shipment_id);
CREATE INDEX idx_shipment_products_shipment ON public.shipment_products(shipment_id);

-- Carbon & compliance indexes
CREATE INDEX idx_carbon_calculations_company ON public.carbon_calculations(company_id);
CREATE INDEX idx_carbon_calculations_product ON public.carbon_calculations(product_id);
CREATE INDEX idx_carbon_targets_company ON public.carbon_targets(company_id);
CREATE INDEX idx_market_readiness_company ON public.market_readiness(company_id);
CREATE INDEX idx_certificates_company ON public.certificates(company_id);
CREATE INDEX idx_reports_company ON public.reports(company_id);

-- Supplier & materials indexes
CREATE INDEX idx_suppliers_company ON public.suppliers(company_id);
CREATE INDEX idx_materials_category ON public.materials(category);
CREATE INDEX idx_emission_factors_category ON public.emission_factors(category, subcategory);

-- B2C indexes
CREATE INDEX idx_donations_user ON public.donations(user_id);
CREATE INDEX idx_donations_status ON public.donations(status);
CREATE INDEX idx_donation_items_donation ON public.donation_items(donation_id);
CREATE INDEX idx_pickup_bookings_user ON public.pickup_bookings(user_id);
CREATE INDEX idx_pickup_bookings_donation ON public.pickup_bookings(donation_id);
CREATE INDEX idx_user_rewards_user ON public.user_rewards(user_id);
CREATE INDEX idx_reward_transactions_user ON public.reward_transactions(user_id);
CREATE INDEX idx_collection_points_city ON public.collection_points(city);
CREATE INDEX idx_collection_points_active ON public.collection_points(is_active);

-- Chat indexes
CREATE INDEX idx_chat_conversations_user ON public.chat_conversations(user_id);
CREATE INDEX idx_chat_messages_conversation ON public.chat_messages(conversation_id);


-- =============================================
-- 29. TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- =============================================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON public.companies FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_shipments_updated_at BEFORE UPDATE ON public.shipments FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON public.suppliers FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_materials_updated_at BEFORE UPDATE ON public.materials FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_emission_factors_updated_at BEFORE UPDATE ON public.emission_factors FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_carbon_targets_updated_at BEFORE UPDATE ON public.carbon_targets FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_market_readiness_updated_at BEFORE UPDATE ON public.market_readiness FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_certificates_updated_at BEFORE UPDATE ON public.certificates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_reports_updated_at BEFORE UPDATE ON public.reports FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_ai_recommendations_updated_at BEFORE UPDATE ON public.ai_recommendations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_collection_points_updated_at BEFORE UPDATE ON public.collection_points FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_donations_updated_at BEFORE UPDATE ON public.donations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_user_rewards_updated_at BEFORE UPDATE ON public.user_rewards FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_chat_conversations_updated_at BEFORE UPDATE ON public.chat_conversations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


-- =============================================
-- 30. HELPER FUNCTIONS
-- =============================================

-- Check if user has specific app role (b2b/b2c/admin)
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  );
$$ LANGUAGE sql STABLE;

-- Check if user has specific company role (admin/member/viewer)
CREATE OR REPLACE FUNCTION public.has_company_role(_user_id UUID, _company_id UUID, _role company_role)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.company_members
    WHERE user_id = _user_id
      AND company_id = _company_id
      AND role = _role
      AND status = 'active'
  )
$$;

-- Check if user is company admin
CREATE OR REPLACE FUNCTION public.is_company_admin(_user_id UUID, _company_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.company_members
    WHERE user_id = _user_id
      AND company_id = _company_id
      AND role = 'admin'
      AND status = 'active'
  )
$$;

-- Cleanup expired refresh tokens (call periodically)
CREATE OR REPLACE FUNCTION public.cleanup_expired_refresh_tokens()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM public.refresh_tokens
  WHERE expires_at < now() OR is_revoked = true;
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Cleanup demo users (call daily)
CREATE OR REPLACE FUNCTION public.cleanup_demo_users()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM public.users
  WHERE is_demo_user = true AND demo_expires_at < now();
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Revoke all refresh tokens for a user (token reuse detection)
CREATE OR REPLACE FUNCTION public.revoke_all_user_tokens(_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
  revoked_count INTEGER;
BEGIN
  UPDATE public.refresh_tokens
  SET is_revoked = true, revoked_at = now()
  WHERE user_id = _user_id AND is_revoked = false;
  
  GET DIAGNOSTICS revoked_count = ROW_COUNT;
  RETURN revoked_count;
END;
$$ LANGUAGE plpgsql;


-- =============================================
-- END OF SCHEMA
-- =============================================
