create table if not exists zones (
    zone_code text primary key,
    zone_name text not null,
    country text not null,
    lat double not null,
    lon double not null
);

create table if not exists border_pairs (
    from_zone text not null,
    to_zone text not null,
    label text not null,
    active boolean not null default true,
    notes text,
    primary key (from_zone, to_zone)
);

create table if not exists border_assets (
    from_zone text not null,
    to_zone text not null,
    asset_name text not null,
    asset_type text not null,
    nominal_capacity_mw double not null,
    source_url text,
    notes text,
    primary key (from_zone, to_zone, asset_name)
);

create table if not exists power_flows_hourly (
    timestamp_utc timestamp not null,
    from_zone text not null,
    to_zone text not null,
    mw double not null,
    source_revision text,
    fetched_at timestamp not null,
    primary key (timestamp_utc, from_zone, to_zone)
);

create table if not exists transfer_capacities_hourly (
    timestamp_utc timestamp not null,
    from_zone text not null,
    to_zone text not null,
    capacity_mw double not null,
    capacity_type text not null,
    source_revision text,
    fetched_at timestamp not null,
    primary key (timestamp_utc, from_zone, to_zone, capacity_type)
);

create table if not exists generation_hourly (
    timestamp_utc timestamp not null,
    zone_code text not null,
    production_type text not null,
    mw double not null,
    source_revision text,
    fetched_at timestamp not null,
    primary key (timestamp_utc, zone_code, production_type)
);

create table if not exists prices_hourly (
    timestamp_utc timestamp not null,
    zone_code text not null,
    eur_per_mwh double not null,
    fetched_at timestamp not null,
    primary key (timestamp_utc, zone_code)
);

create table if not exists ingestion_runs (
    run_id uuid primary key,
    dataset text not null,
    started_at timestamp not null,
    finished_at timestamp,
    status text not null,
    rows_loaded integer,
    error text
);
