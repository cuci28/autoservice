function getMessageEl(form) {
  return form.querySelector('[data-message]');
}

function showMessage(form, text, type) {
  const messageEl = getMessageEl(form);
  if (!messageEl) {
    return;
  }
  messageEl.textContent = text;
  messageEl.classList.remove('is-success', 'is-error');
  if (type) {
    messageEl.classList.add(type === 'error' ? 'is-error' : 'is-success');
  }
}

function buildPayloadFromForm(form, fields) {
  const payload = {};
  for (const field of fields) {
    const value = form.querySelector(`[name="${field}"]`)?.value ?? '';
    payload[field] = value;
  }
  return payload;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.details || 'Ошибка запроса');
  }
  return data;
}

async function deleteJson(url) {
  const response = await fetch(url, {
    method: 'DELETE',
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.details || 'Ошибка запроса');
  }
  return data;
}

function initSimpleForm(formId, endpoint, payloadBuilder, afterSuccess) {
  const form = document.getElementById(formId);
  if (!form) {
    return;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const successText = form.dataset.successText || 'Сохранено';
    try {
      const payload = payloadBuilder(form);
      const result = await postJson(endpoint, payload);
      showMessage(form, successText, 'success');
      form.reset();
      if (afterSuccess) {
        afterSuccess(result, form);
      }
    } catch (error) {
      showMessage(form, error.message, 'error');
    }
  });
}

function syncQtyInputs() {
  document.querySelectorAll('.choice-item').forEach((item) => {
    const checkbox = item.querySelector('input[type="checkbox"]');
    const qty = item.querySelector('.choice-qty');
    if (!checkbox || !qty) {
      return;
    }

    const syncState = () => {
      qty.disabled = !checkbox.checked;
    };

    checkbox.addEventListener('change', syncState);
    syncState();
  });
}

function calculateOrderTotal() {
  let total = 0;

  document.querySelectorAll('.service-check').forEach((checkbox) => {
    if (!checkbox.checked) {
      return;
    }
    const qty = Number(checkbox.closest('.choice-item')?.querySelector('.choice-qty')?.value || 1);
    const price = Number(checkbox.dataset.price || 0);
    total += qty * price;
  });

  document.querySelectorAll('.part-check').forEach((checkbox) => {
    if (!checkbox.checked) {
      return;
    }
    const qty = Number(checkbox.closest('.choice-item')?.querySelector('.choice-qty')?.value || 1);
    const price = Number(checkbox.dataset.price || 0);
    total += qty * price;
  });

  const totalEl = document.getElementById('order-total');
  if (totalEl) {
    totalEl.textContent = `${total} ₽`;
  }
}

function collectItems(selector) {
  return Array.from(document.querySelectorAll(selector))
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => {
      const qty = Number(checkbox.closest('.choice-item')?.querySelector('.choice-qty')?.value || 1);
      return {
        id: Number(checkbox.dataset.id),
        quantity: qty,
      };
    });
}

function initOrderForm() {
  const form = document.getElementById('order-form');
  if (!form) {
    return;
  }

  syncQtyInputs();
  calculateOrderTotal();

  form.addEventListener('input', calculateOrderTotal);
  form.addEventListener('change', calculateOrderTotal);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    showMessage(form, 'Создаем заказ...', null);

    const payload = {
      car_id: Number(form.querySelector('[name="car_id"]').value),
      master_id: form.querySelector('[name="master_id"]').value ? Number(form.querySelector('[name="master_id"]').value) : null,
      services: collectItems('.service-check').map((item) => ({ service_id: item.id, quantity: item.quantity })),
      parts: collectItems('.part-check').map((item) => ({ part_id: item.id, quantity: item.quantity })),
    };

    if (!payload.car_id) {
      showMessage(form, 'Выберите машину', 'error');
      return;
    }

    try {
      const result = await postJson('/api/orders', payload);
      window.location.href = `/orders/${result.order_id}/receipt`;
    } catch (error) {
      showMessage(form, error.message, 'error');
    }
  });
}

function initMasterDeletion() {
  document.querySelectorAll('[data-delete-master]').forEach((button) => {
    button.addEventListener('click', async () => {
      const masterId = button.dataset.deleteMaster;
      if (!window.confirm('Удалить мастера?')) {
        return;
      }

      try {
        await deleteJson(`/api/masters/${masterId}`);
      } catch (error) {
        alert(error.message);
        return;
      }

      window.location.reload();
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initSimpleForm('client-form', '/api/clients-with-car', (form) => ({
    full_name: form.querySelector('[name="full_name"]').value.trim(),
    phone_number: form.querySelector('[name="phone_number"]').value.trim(),
    email: form.querySelector('[name="email"]').value.trim() || null,
    car: {
      car_model: form.querySelector('[name="car_model"]').value.trim(),
      year: Number(form.querySelector('[name="year"]').value),
      vin: form.querySelector('[name="vin"]').value.trim(),
    },
  }));

  initSimpleForm('master-form', '/api/masters', (form) => ({
    master_name: form.querySelector('[name="master_name"]').value.trim(),
    phone_number: form.querySelector('[name="phone_number"]').value.trim(),
    email: form.querySelector('[name="email"]').value.trim() || null,
  }), () => window.location.reload());

  initSimpleForm('warehouse-form', '/api/warehouse/incoming', (form) => ({
    part_id: Number(form.querySelector('[name="part_id"]').value),
    quantity: Number(form.querySelector('[name="quantity"]').value),
  }), () => window.location.reload());

  initSimpleForm('warehouse-writeoff-form', '/api/warehouse/writeoff', (form) => ({
    part_id: Number(form.querySelector('[name="part_id"]').value),
    quantity: Number(form.querySelector('[name="quantity"]').value),
  }), () => window.location.reload());

  initOrderForm();
  initMasterDeletion();
});
