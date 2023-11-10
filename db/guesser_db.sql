create table if not exists GameType
(
    id              INTEGER not null primary key autoincrement,
    name            TEXT    not null,
    game_pattern    TEXT,
    scoring_pattern TEXT,
    publish_date    DATETIME
);

create table if not exists Game
(
    id           INTEGER not null primary key autoincrement,
    game_type_id INTEGER not null
        constraint Game_game_type_id_fkey references GameType on update cascade on delete restrict,
    identifier   TEXT    not null,
    name         TEXT,
    post_date    DATETIME
);

create unique index if not exists Game_identifier_key
    on Game (identifier);

create unique index if not exists GameType_name_key
    on GameType (name);

create table if not exists Player
(
    id         INTEGER                            not null primary key autoincrement,
    join_date  DATETIME default CURRENT_TIMESTAMP not null,
    id_hash    TEXT                               not null,
    id_enc     TEXT                               not null,
    active     BOOLEAN  default true              not null,
    visible    BOOLEAN  default true              not null
);

create unique index if not exists Player_id_hash_key
    on Player (id_hash);

create unique index if not exists Player_id_enc_key
    on Player (id_enc);

create table if not exists Result
(
    id          INTEGER not null primary key autoincrement,
    player_id   INTEGER not null
        constraint Result_player_id_fkey references Player on update cascade on delete restrict,
    game_id     INTEGER not null
        constraint Result_game_id_fkey references Game on update cascade on delete restrict,
    submit_time DATETIME default CURRENT_TIMESTAMP,
    guesses     INTEGER not null
);

