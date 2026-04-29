-- Adds Nature Mint to shop_items.
-- Run once in Supabase SQL Editor.

INSERT INTO shop_items (slug, name, description, icon, category, price, effect_stat, effect_value)
VALUES (
    'nature-mint',
    'Nature Mint',
    'Troca a natureza de um Pokémon por qualquer outra à sua escolha. Efeito permanente.',
    '🌿',
    'nature_mint',
    75,
    NULL,
    NULL
)
ON CONFLICT (slug) DO UPDATE
    SET name        = EXCLUDED.name,
        description = EXCLUDED.description,
        icon        = EXCLUDED.icon,
        category    = EXCLUDED.category,
        price       = EXCLUDED.price;
