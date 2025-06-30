--
-- PostgreSQL database dump
--

-- Dumped from database version 17rc1
-- Dumped by pg_dump version 17rc1

-- Started on 2025-06-19 21:28:20

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 6 (class 2615 OID 26106)
-- Name: schema; Type: SCHEMA; Schema: -; Owner: real_estate_admin
--

CREATE SCHEMA schema;


ALTER SCHEMA schema OWNER TO real_estate_admin;

--
-- TOC entry 850 (class 1247 OID 17981)
-- Name: property_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.property_type AS ENUM (
    'Квартира',
    'Частный дом',
    'Таунхаус',
    'Коммерческая недвижимость',
    'Земельный участок'
);


ALTER TYPE public.property_type OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 221 (class 1259 OID 18002)
-- Name: listings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.listings (
    id integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    price numeric(14,2) NOT NULL,
    city character varying(100) NOT NULL,
    address character varying(255),
    district character varying(50),
    area numeric(6,2),
    rooms integer,
    property_type public.property_type NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying,
    user_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT listings_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'sold'::character varying, 'archived'::character varying])::text[])))
);


ALTER TABLE public.listings OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 18001)
-- Name: listings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.listings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.listings_id_seq OWNER TO postgres;

--
-- TOC entry 4821 (class 0 OID 0)
-- Dependencies: 220
-- Name: listings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.listings_id_seq OWNED BY public.listings.id;


--
-- TOC entry 219 (class 1259 OID 17992)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    login character varying(50) NOT NULL,
    password character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    phone character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    role character varying(20) DEFAULT 'agent'::character varying NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 17991)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 4824 (class 0 OID 0)
-- Dependencies: 218
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 4654 (class 2604 OID 18005)
-- Name: listings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.listings ALTER COLUMN id SET DEFAULT nextval('public.listings_id_seq'::regclass);


--
-- TOC entry 4651 (class 2604 OID 17995)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 4663 (class 2606 OID 18012)
-- Name: listings listings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.listings
    ADD CONSTRAINT listings_pkey PRIMARY KEY (id);


--
-- TOC entry 4659 (class 2606 OID 18000)
-- Name: users users_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_login_key UNIQUE (login);


--
-- TOC entry 4661 (class 2606 OID 17998)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 4664 (class 2606 OID 18013)
-- Name: listings listings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.listings
    ADD CONSTRAINT listings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4819 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO real_estate_admin;
GRANT USAGE ON SCHEMA public TO real_estate_agent;


--
-- TOC entry 4820 (class 0 OID 0)
-- Dependencies: 221
-- Name: TABLE listings; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.listings TO real_estate_admin;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.listings TO real_estate_agent;


--
-- TOC entry 4822 (class 0 OID 0)
-- Dependencies: 220
-- Name: SEQUENCE listings_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.listings_id_seq TO real_estate_admin;
GRANT SELECT,USAGE ON SEQUENCE public.listings_id_seq TO real_estate_agent;


--
-- TOC entry 4823 (class 0 OID 0)
-- Dependencies: 219
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.users TO real_estate_admin;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.users TO real_estate_agent;


--
-- TOC entry 4825 (class 0 OID 0)
-- Dependencies: 218
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.users_id_seq TO real_estate_admin;
GRANT SELECT,USAGE ON SEQUENCE public.users_id_seq TO real_estate_agent;


--
-- TOC entry 2053 (class 826 OID 18023)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: real_estate_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE real_estate_admin IN SCHEMA public GRANT ALL ON TABLES TO real_estate_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE real_estate_admin IN SCHEMA public GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO real_estate_agent;


-- Completed on 2025-06-19 21:28:20

--
-- PostgreSQL database dump complete
--

