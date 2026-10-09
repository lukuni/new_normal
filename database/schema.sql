-- Залуу Дуу Хоолой: PostgreSQL schema (generated from backend/app/models.py via pg_dump).
-- The backend creates these tables automatically on start; this file is for review / manual setup.


-- Name: anchors; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.anchors (
    id integer NOT NULL,
    from_index integer NOT NULL,
    to_index integer NOT NULL,
    merkle_root character varying(64) NOT NULL,
    network character varying(40) NOT NULL,
    tx_hash character varying(80),
    created_at timestamp with time zone NOT NULL
);

-- Name: anchors_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.anchors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: anchors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.anchors_id_seq OWNED BY public.anchors.id;

-- Name: consultations; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.consultations (
    id integer NOT NULL,
    title character varying(300) NOT NULL,
    summary text NOT NULL,
    law_reference character varying(300) NOT NULL,
    organizer character varying(200) NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    closes_at timestamp with time zone
);

-- Name: consultations_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.consultations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: consultations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.consultations_id_seq OWNED BY public.consultations.id;

-- Name: ledger_blocks; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.ledger_blocks (
    index integer NOT NULL,
    "timestamp" character varying(40) NOT NULL,
    proposal_id integer NOT NULL,
    category character varying(60) NOT NULL,
    content_hash character varying(64) NOT NULL,
    prev_hash character varying(64) NOT NULL,
    block_hash character varying(64) NOT NULL
);

-- Name: proposals; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.proposals (
    id integer NOT NULL,
    consultation_id integer,
    text text,
    age_group character varying(20) NOT NULL,
    location character varying(60) NOT NULL,
    category character varying(60) NOT NULL,
    sentiment character varying(30) NOT NULL,
    urgency character varying(20) NOT NULL,
    confidence double precision NOT NULL,
    classifier character varying(30) NOT NULL,
    content_hash character varying(64) NOT NULL,
    status character varying(20) NOT NULL,
    response_note text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    erased_at timestamp with time zone,
    owner_secret_hash character varying(64) NOT NULL
);

-- Name: proposals_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.proposals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: proposals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.proposals_id_seq OWNED BY public.proposals.id;

-- Name: anchors id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.anchors ALTER COLUMN id SET DEFAULT nextval('public.anchors_id_seq'::regclass);

-- Name: consultations id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.consultations ALTER COLUMN id SET DEFAULT nextval('public.consultations_id_seq'::regclass);

-- Name: proposals id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.proposals ALTER COLUMN id SET DEFAULT nextval('public.proposals_id_seq'::regclass);

-- Name: anchors anchors_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.anchors
    ADD CONSTRAINT anchors_pkey PRIMARY KEY (id);

-- Name: consultations consultations_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_pkey PRIMARY KEY (id);

-- Name: ledger_blocks ledger_blocks_block_hash_key; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.ledger_blocks
    ADD CONSTRAINT ledger_blocks_block_hash_key UNIQUE (block_hash);

-- Name: ledger_blocks ledger_blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.ledger_blocks
    ADD CONSTRAINT ledger_blocks_pkey PRIMARY KEY (index);

-- Name: ledger_blocks ledger_blocks_proposal_id_key; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.ledger_blocks
    ADD CONSTRAINT ledger_blocks_proposal_id_key UNIQUE (proposal_id);

-- Name: proposals proposals_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.proposals
    ADD CONSTRAINT proposals_pkey PRIMARY KEY (id);

-- Name: ix_proposals_category; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_proposals_category ON public.proposals USING btree (category);

-- Name: ix_proposals_consultation_id; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_proposals_consultation_id ON public.proposals USING btree (consultation_id);

-- Name: ix_proposals_content_hash; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_proposals_content_hash ON public.proposals USING btree (content_hash);

-- Name: ix_proposals_status; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_proposals_status ON public.proposals USING btree (status);

-- Name: ledger_blocks ledger_blocks_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.ledger_blocks
    ADD CONSTRAINT ledger_blocks_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id);

-- Name: proposals proposals_consultation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.proposals
    ADD CONSTRAINT proposals_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id);

