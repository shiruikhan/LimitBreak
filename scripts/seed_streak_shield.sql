-- Insere o item Streak Shield na loja.
-- Executar uma vez no SQL Editor do Supabase.

INSERT INTO shop_items (slug, name, description, icon, category, price)
VALUES (
    'streak-shield',
    'Escudo de Streak',
    'Protege seu streak por um dia perdido. Consumido automaticamente no check-in.',
    '🛡️',
    'other',
    100
)
ON CONFLICT (slug) DO NOTHING;
