create table public.documents (
    id uuid primary key default gen_random_uuid(),

    company_id uuid not null
        references public.companies(id)
        on delete cascade,

    uploaded_by uuid not null
        references auth.users(id)
        on delete cascade,

    name text not null,

    storage_path text not null,

    file_type text not null,

    file_size bigint,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now()
);


alter table public.documents
add constraint documents_file_type_check
check (
    file_type in (
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    )
);

alter table public.documents
enable row level security;

create policy "Users can view documents from their company"
on public.documents
for select
to authenticated
using (
    company_id = (
        select company_id
        from public.profiles
        where id = auth.uid()
    )
);

create policy "Users can upload documents to their company"
on public.documents
for insert
to authenticated
with check (
    company_id = (
        select company_id
        from public.profiles
        where id = auth.uid()
    )
);

create policy "Users can delete documents from their company"
on public.documents
for delete
to authenticated
using (
    company_id = (
        select company_id
        from public.profiles
        where id = auth.uid()
    )
);


create policy "Users can update documents from their company"
on public.documents
for update
to authenticated
using (
    company_id = (
        select company_id
        from public.profiles
        where id = auth.uid()
    )
)
with check (
    company_id = (
        select company_id
        from public.profiles
        where id = auth.uid()
    )
);