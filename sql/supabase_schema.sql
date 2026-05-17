create table if not exists zones (
    zone_code text primary key,
    zone_name text not null,
    country text not null,
    lat double precision not null,
    lon double precision not null
);

create table if not exists border_pairs (
    from_zone text not null references zones(zone_code),
    to_zone text not null references zones(zone_code),
    label text not null,
    active boolean not null default true,
    notes text,
    primary key (from_zone, to_zone)
);

create table if not exists border_assets (
    from_zone text not null references zones(zone_code),
    to_zone text not null references zones(zone_code),
    asset_name text not null,
    asset_type text not null,
    nominal_capacity_mw double precision not null,
    source_url text,
    notes text,
    primary key (from_zone, to_zone, asset_name)
);

create table if not exists power_flows_hourly (
    timestamp_utc timestamptz not null,
    from_zone text not null references zones(zone_code),
    to_zone text not null references zones(zone_code),
    mw double precision not null,
    source_revision text,
    fetched_at timestamptz not null,
    primary key (timestamp_utc, from_zone, to_zone)
);

create table if not exists transfer_capacities_hourly (
    timestamp_utc timestamptz not null,
    from_zone text not null references zones(zone_code),
    to_zone text not null references zones(zone_code),
    capacity_mw double precision not null,
    capacity_type text not null,
    source_revision text,
    fetched_at timestamptz not null,
    primary key (timestamp_utc, from_zone, to_zone, capacity_type)
);

create table if not exists generation_hourly (
    timestamp_utc timestamptz not null,
    zone_code text not null references zones(zone_code),
    production_type text not null,
    mw double precision not null,
    source_revision text,
    fetched_at timestamptz not null,
    primary key (timestamp_utc, zone_code, production_type)
);

create table if not exists prices_hourly (
    timestamp_utc timestamptz not null,
    zone_code text not null references zones(zone_code),
    eur_per_mwh double precision not null,
    fetched_at timestamptz not null,
    primary key (timestamp_utc, zone_code)
);

create table if not exists ingestion_runs (
    run_id uuid primary key,
    dataset text not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    status text not null,
    rows_loaded integer,
    error text
);

create index if not exists idx_power_flows_hourly_timestamp
    on power_flows_hourly (timestamp_utc desc);

create index if not exists idx_transfer_capacities_hourly_timestamp
    on transfer_capacities_hourly (timestamp_utc desc);

create index if not exists idx_ingestion_runs_started_at
    on ingestion_runs (started_at desc);
