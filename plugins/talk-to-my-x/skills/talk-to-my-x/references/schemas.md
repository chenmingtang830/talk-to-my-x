[//]: # (ob:67dc2f0b)
# Local state schemas

[//]: # (ob:3d9d38f0)
## Ingested post

[//]: # (ob:4ee06f10)
Required: `id`, `text` (or News `title`), HTTPS `url`, and `source`. Include
`author`, `name`, `created_at`, and `metrics` when available.

[//]: # (ob:4d542853)
Sources: `timeline`, `bookmarks`, `search`, `news`, `priority_accounts`,
`user_posts`.

[//]: # (ob:99c08a1e)
## Reaction Card

[//]: # (ob:74b39d8e)
Required: non-empty `sources` and `raw_reaction`. Optional: existing `id`,
`summary`, `stance`, `questions`, `connections`, and status `open`,
`developing`, `ready`, `drafted`, or `archived`.

[//]: # (ob:548f44f0)
## Draft

[//]: # (ob:78947686)
Provide exactly one of `text` or `thread`, a non-empty `sources` array, optional
`card_ids`, optional existing `id`, and optional `edit_summary`. Every post is
at most 280 characters.

[//]: # (ob:a546ab5c)
## Action

[//]: # (ob:367d5303)
`prepare_action` requires `type` and its exact target. Post/reply also requires
text or thread. `complete_action` requires `action_id`, terminal `status`, and
for `succeeded`/`partial`, the exact `confirmation`. Put public X IDs and URLs
under `result`; never include credentials.

[//]: # (ob:127562d0)
## Memory

[//]: # (ob:6d0db7ae)
Provide complete `taste_md` and `voice_md`, a non-empty `rationale`, and
`evidence_refs`. Evidence types are `reaction`, `draft_revision`, `signal`, and
completed `action`; revision and signal refs also include their specific
revision or signal ID.

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwXzE3MzE4MGQ3Y2VkMjhhYmM5YzcwMjcyZCIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6IjA3MWJkMmRkIiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV85Yjc0MDgxYTZkZGRhYzc0MWQ3MTUyOTQiLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsXzg5MTYyNjE5OWJhMTNkNjY4ZGRmZTY3YiIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNrFWG1v3LgR_ivE3pcWXXv1_rL9VDQFGuDaBrncocA5kPgy2mVXK-pIys7CyH_vkJJ2106qnJ0PBQxbpMjhzDMP5xn5cUW1lQ3ltpJitV31fRXmcVgEIucgooIyXvI8iPJIrNYrpsSpEnIHxuJas6dRmm2jIm0KSjkUIoIwzyMe0SwMMmjSJhFpkzORFHES0iQvslRkUcbigrOkFEkZsjhCu0Iaru5Bn1bbRzewlaU7PKGl1h21xgcGLU78Alo2krIWiIZ7aaTqyB7XK30i7ETeaaWaXoMxuKen_EB34IJ6Mq3VfwDDHbQzuLe2N9vNZiftfmC3XB03fA_dUXY7S7tdEQebJ7s1_DZIfK4GA7riqjPQIRZWD_B5vdoDdSAGechEJBxibqaCe78IwYWqZHkSFCHNhBCU50ko8jCNysR5prR1oVWt7AA9nzPSVkUZImxhWTIaxiLLCiEayHI2hjN5V3Ham6HFgCPnJ1damNX218fVdPzjCrOstHFP42sQFUPIf10N3aFTD93qI8Yw88Ed3Q472ZmNpe3hxqqb4-nm08YcZNs-m9PQgIaOg9kYhO9Ize3RRf8SblFrtWSDxZRWjBppHMOgbSpqEGoLfs1g90q7AA6ycybNyVg44puOHl2m50DWuNU4dqy23dC2GBbfYzphBIS1ih9wdZYLHjWBgxEzaeGTC_pHxWlLjEXqkSkYfD-dR4XwjvSOffCAMz-Qr2-wp9455PKPXFp9Xl-OjUUp4qIJnhz71nmHUZJeecb_7wN_IM_XLpyVAARZE77yrPcj28WW1FLUa1I7AzX5g9Lkn_BgcCxtC_Uf1-TvHz68-4nUeKlwGe0EqS9-9VTTp06JNMGqEb_OqZ_UoJFpW3f6EdxdcZ4xpQ5Hqg_GDQxQzffuqUM33d9eS6WlXXCqLHlQ0BCeOPUekL2uyPyVavGNrDxfu5CVPGFxKYpXnnXJSqe6Gzj29oQhj6jUI_iaPlR6slffkn_17oG2W7IAQJoUTZI8o-UbTZtv0XFesxRwUSZ5VmQvs43l_F4KIPAJI2lPRHVAVDOzEElY2z1G6ZhJn2OxEChNk4yylD9x5i8eq29Eel60dLuxqqRxEL_QOjIU0FOopqSRWWkwSDxszKu0ZgSDWKp3YG_JO7wsm4VYwyhPs0g8Teo_4IiC-Y1Yz4sWYs1EIFhO4YXW57yi2vYtYNmsLcWrXx3FRN97JbkfPkuspl_c4I_rWd9W2EC4kl9x5MSoF_7NLD6L2tsp621OEkwmCSZYz_mhV7KzvqPQ_iQnKfPIKcpHp92t5KcrC9d6fmXEdwqvlHqjGls1mAPQWM6mjsKwcFumEeQsYKJkSVoKCBtgRRClLBdhBkkY4S-ecMFFUNIk4EEcJmUJMSvihsWxuwhOvnxnMGZrG0aomW5mFQVRdhPkN1HxIQi2aYKv_oQPgaPUhPh1y_P5avbx_9ZMeIKOYr-nZo_reYx4JixMKYS4wNu40v-Juy9Q88luwEuIIo6opWK2eyXws93fJdqTyTIHETcigTQ-u3ql42e5eL02j2KBwvC24-0g4K6rx9bKSya2Uu7vdI0qaudtR8AWjaPGPGCLTOg9la0j8e1X6s-MepEWnIeCBUVwDuWi_lMo36PoJyyYXA14Ees1huHbcoewqRfcok3KBM0DvBEwu3Wl_5ek_Q5Nn0xCUSR5GEKUZWceXMn8F0l7uXTDJ_zQwVPHfGOsZjgiPicPD36scI_abwOyDHd4jLAod8DnoTPviD0gOVQPnTcisEa2qke7boNTU29QOG0Gxysnsw57eY_DBUwzztIwzptI5GcArlqKC6YL7cJkKmYxyyj-Tik7Y3npICZT39MdjHBrTU8Y4IQwgsExy1heHFjz7DPYPYjndzUIaas5D7fkb-4b1l9wIs1dRy05uueoCFBIEC9usTQuYChCHmUxw69iiObAr7qVC4ZLjchkK0EAaUlDrERnW1e9yWTre9oO3Imw09ao86473wQ48Efsbx0HR5H_ygnjTOVxRWTwo9thOlJ0hPqua1wizcA5AApTval7pwPUlTK7n5Lvid5IfaTTpXk3WNIPDCWZ_Ju8fWN8FD-__xH9GzoB2hEdP5Vt_WfSIf81kWMdJFjzBIo62l9KU1kESRgGkOTpuapdNVqXNC31UJOtJkxQlXlW5jw969KlrXrG9dd0TJ6qMONZgzOExQKLTGM8Z8cxcT4iUhp8GRiTNVeCav5viy82ctfRdjY4uyTmfCKo5__N-JLjlxN33EiWGWzMn9TE9MBlI_ldd96FKZ82vX3zRRo-fsaf_wIZHy0T)
