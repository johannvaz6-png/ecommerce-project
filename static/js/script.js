const message = (text, error = false) => {
    const box = document.querySelector('#api-message');

    if (box) {
        box.innerHTML = `<div class="message ${error ? 'error' : 'success'}">${text}</div>`;
    }
};

const escapeHtml = value =>
    String(value).replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[char]));

const formatINR = value =>
    new Intl.NumberFormat('en-IN', {
        maximumFractionDigits: 0
    }).format(value);

async function api(url, options = {}) {
    const r = await fetch(url, {
        headers: {
            'Content-Type': 'application/json'
        },
        ...options
    });

    const d = await r.json();

    if (!r.ok) {
        throw Error(d.error || 'Something went wrong.');
    }

    return d;
}

document.querySelector('.nav-toggle')?.addEventListener('click', () =>
    document.querySelector('.nav-links').classList.toggle('open')
);

if (document.querySelector('#products')) {
    api('/api/products')
        .then(({ products }) => {
            document.querySelector('#product-count').textContent =
                `${products.length} items`;

            document.querySelector('#products').innerHTML = products
                .map(p => {
                    const name = escapeHtml(p.name);
                    const category = escapeHtml(p.category);
                    const description = escapeHtml(p.description);
                    const image = escapeHtml(p.image);

                    const visual = image
                        ? `<img class="product-image" style="width:100%;height:100%;object-fit:fill" src="${image}" alt="${name}">`
                        : `<div class="product-image">${category[0] || 'P'}</div>`;

                    return `<article class="product">${visual}<p class="eyebrow">${category}</p><h3>${name}</h3><p>${description}</p><p class="price">₹${formatINR(p.price)}</p><p class="stock ${p.stock ? '' : 'out'}">${p.stock ? `${p.stock} available` : 'Out of stock'}</p><a class="button secondary" href="/products/${p.id}">View details</a></article>`;
                })
                .join('');
        })
        .catch(e => message(e.message, true));
}

document.querySelectorAll('.add-cart').forEach(b =>
    b.addEventListener('click', async () => {
        try {
            await api('/api/cart', {
                method: 'POST',
                body: JSON.stringify({
                    product_id: +b.dataset.product,
                    quantity: 1
                })
            });

            message('Product added to your cart.');
        } catch (e) {
            message(e.message, true);
        }
    })
);

document.querySelectorAll('.quantity button').forEach(b =>
    b.addEventListener('click', async () => {
        try {
            if (+b.dataset.quantity < 1) return;

            await api(`/api/cart/${b.dataset.cartId}`, {
                method: 'PUT',
                body: JSON.stringify({
                    quantity: +b.dataset.quantity
                })
            });

            location.reload();
        } catch (e) {
            message(e.message, true);
        }
    })
);

document.querySelectorAll('.remove-cart').forEach(b =>
    b.addEventListener('click', async () => {
        try {
            await api(`/api/cart/${b.dataset.cartId}`, {
                method: 'DELETE'
            });

            location.reload();
        } catch (e) {
            message(e.message, true);
        }
    })
);

const form = document.querySelector('#product-form');

document.querySelector('#new-product')?.addEventListener('click', () => {
    form.reset();
    form.elements.id.value = '';
    document.querySelector('#form-title').textContent = 'Add product';
    form.classList.remove('hidden');
});

document.querySelectorAll('.edit-product').forEach(b =>
    b.addEventListener('click', () => {
        const p = JSON.parse(b.closest('tr').dataset.product);

        Object.entries(p).forEach(([k, v]) =>
            form.elements[k] && (form.elements[k].value = v)
        );

        document.querySelector('#form-title').textContent = 'Edit product';
        form.classList.remove('hidden');

        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    })
);

form?.addEventListener('submit', async e => {
    e.preventDefault();

    const data = Object.fromEntries(new FormData(form));
    const id = data.id;

    delete data.id;

    try {
        await api(id ? `/api/products/${id}` : '/api/products', {
            method: id ? 'PUT' : 'POST',
            body: JSON.stringify(data)
        });

        location.reload();
    } catch (e) {
        message(e.message, true);
    }
});

document.querySelectorAll('.delete-product').forEach(b =>
    b.addEventListener('click', async () => {
        if (!confirm('Delete this product?')) return;

        try {
            await api(`/api/products/${b.dataset.id}`, {
                method: 'DELETE'
            });

            location.reload();
        } catch (e) {
            message(e.message, true);
        }
    })
);

document.querySelectorAll('.order-status').forEach(s =>
    s.addEventListener('change', async () => {
        try {
            await api(`/api/orders/${s.dataset.id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    status: s.value
                })
            });

            message('Order status updated.');
        } catch (e) {
            message(e.message, true);
        }
    })
);