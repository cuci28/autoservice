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

async function patchJson(url, payload) {
  const response = await fetch(url, {
    method: 'PATCH',
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

function initPartEditing() {
  document.querySelectorAll('.part-row').forEach((row) => {
    const partId = Number(row.dataset.partId);
    const nameText = row.querySelector('.part-name-text');
    const nameInput = row.querySelector('.part-name-input');
    const priceText = row.querySelector('.part-price-text');
    const priceInput = row.querySelector('.part-price-input');
    const editBtn = row.querySelector('.part-edit-btn');
    const saveBtn = row.querySelector('.part-save-btn');
    const cancelBtn = row.querySelector('.part-cancel-btn');

    if (!partId || !nameText || !nameInput || !priceText || !priceInput || !editBtn || !saveBtn || !cancelBtn) {
      return;
    }

    const startEdit = () => {
      row.classList.add('is-editing');
      nameText.classList.add('is-hidden');
      priceText.classList.add('is-hidden');
      nameInput.classList.remove('is-hidden');
      priceInput.classList.remove('is-hidden');
      editBtn.classList.add('is-hidden');
      saveBtn.classList.remove('is-hidden');
      cancelBtn.classList.remove('is-hidden');
      nameInput.focus();
    };

    const stopEdit = () => {
      row.classList.remove('is-editing');
      nameText.classList.remove('is-hidden');
      priceText.classList.remove('is-hidden');
      nameInput.classList.add('is-hidden');
      priceInput.classList.add('is-hidden');
      editBtn.classList.remove('is-hidden');
      saveBtn.classList.add('is-hidden');
      cancelBtn.classList.add('is-hidden');
      nameInput.value = nameText.textContent.trim();
      priceInput.value = priceText.textContent.trim();
    };

    editBtn.addEventListener('click', startEdit);

    cancelBtn.addEventListener('click', () => {
      stopEdit();
    });

    saveBtn.addEventListener('click', async () => {
      const nextName = nameInput.value.trim();
      const nextPrice = Number(priceInput.value);

      if (!nextName) {
        alert('Название не может быть пустым');
        return;
      }
      if (!Number.isFinite(nextPrice) || nextPrice <= 0) {
        alert('Цена должна быть числом больше нуля');
        return;
      }

      try {
        await patchJson(`/api/warehouse/parts/${partId}`, {
          part_name: nextName,
          unit_price: nextPrice,
        });
      } catch (error) {
        alert(error.message);
        return;
      }

      nameText.textContent = nextName;
      priceText.textContent = String(nextPrice);
      stopEdit();
    });
  });
}

function initServiceManagement() {
  initSimpleForm('service-form', '/api/services', (form) => ({
    service_name: form.querySelector('[name="service_name"]').value.trim(),
    price: Number(form.querySelector('[name="price"]').value),
  }), () => window.location.reload());

  document.querySelectorAll('.service-row').forEach((row) => {
    const serviceId = Number(row.dataset.serviceId);
    const nameText = row.querySelector('.service-name-text');
    const nameInput = row.querySelector('.service-name-input');
    const priceText = row.querySelector('.service-price-text');
    const priceInput = row.querySelector('.service-price-input');
    const editBtn = row.querySelector('.service-edit-btn');
    const saveBtn = row.querySelector('.service-save-btn');
    const cancelBtn = row.querySelector('.service-cancel-btn');
    const deleteBtn = row.querySelector('.service-delete-btn');

    if (!serviceId || !nameText || !nameInput || !priceText || !priceInput || !editBtn || !saveBtn || !cancelBtn || !deleteBtn) {
      return;
    }

    const startEdit = () => {
      row.classList.add('is-editing');
      nameText.classList.add('is-hidden');
      priceText.classList.add('is-hidden');
      nameInput.classList.remove('is-hidden');
      priceInput.classList.remove('is-hidden');
      editBtn.classList.add('is-hidden');
      deleteBtn.classList.add('is-hidden');
      saveBtn.classList.remove('is-hidden');
      cancelBtn.classList.remove('is-hidden');
      nameInput.focus();
    };

    const stopEdit = () => {
      row.classList.remove('is-editing');
      nameText.classList.remove('is-hidden');
      priceText.classList.remove('is-hidden');
      nameInput.classList.add('is-hidden');
      priceInput.classList.add('is-hidden');
      editBtn.classList.remove('is-hidden');
      deleteBtn.classList.remove('is-hidden');
      saveBtn.classList.add('is-hidden');
      cancelBtn.classList.add('is-hidden');
      nameInput.value = nameText.textContent.trim();
      priceInput.value = priceText.textContent.trim();
    };

    editBtn.addEventListener('click', startEdit);

    cancelBtn.addEventListener('click', () => {
      stopEdit();
    });

    saveBtn.addEventListener('click', async () => {
      const nextName = nameInput.value.trim();
      const nextPrice = Number(priceInput.value);

      if (!nextName) {
        alert('Название не может быть пустым');
        return;
      }
      if (!Number.isFinite(nextPrice) || nextPrice <= 0) {
        alert('Цена должна быть числом больше нуля');
        return;
      }

      try {
        await patchJson(`/api/services/${serviceId}`, {
          service_name: nextName,
          price: nextPrice,
        });
      } catch (error) {
        alert(error.message);
        return;
      }

      nameText.textContent = nextName;
      priceText.textContent = String(nextPrice);
      stopEdit();
    });

    deleteBtn.addEventListener('click', async () => {
      if (!window.confirm('Удалить услугу?')) {
        return;
      }

      try {
        await deleteJson(`/api/services/${serviceId}`);
      } catch (error) {
        alert(error.message);
        return;
      }

      window.location.reload();
    });
  });
}

function initClientManagement() {
  document.querySelectorAll('.client-row').forEach((row) => {
    const clientId = Number(row.dataset.clientId);
    const nameText = row.querySelector('.client-name-text');
    const nameInput = row.querySelector('.client-name-input');
    const phoneText = row.querySelector('.client-phone-text');
    const phoneInput = row.querySelector('.client-phone-input');
    const emailText = row.querySelector('.client-email-text');
    const emailInput = row.querySelector('.client-email-input');
    const editBtn = row.querySelector('.client-edit-btn');
    const saveBtn = row.querySelector('.client-save-btn');
    const cancelBtn = row.querySelector('.client-cancel-btn');
    const deleteBtn = row.querySelector('.client-delete-btn');

    if (!clientId || !nameText || !nameInput || !phoneText || !phoneInput || !emailText || !emailInput || !editBtn || !saveBtn || !cancelBtn || !deleteBtn) {
      return;
    }

    const startEdit = () => {
      row.classList.add('is-editing');
      nameText.classList.add('is-hidden');
      phoneText.classList.add('is-hidden');
      emailText.classList.add('is-hidden');
      nameInput.classList.remove('is-hidden');
      phoneInput.classList.remove('is-hidden');
      emailInput.classList.remove('is-hidden');
      editBtn.classList.add('is-hidden');
      deleteBtn.classList.add('is-hidden');
      saveBtn.classList.remove('is-hidden');
      cancelBtn.classList.remove('is-hidden');
      nameInput.focus();
    };

    const stopEdit = () => {
      row.classList.remove('is-editing');
      nameText.classList.remove('is-hidden');
      phoneText.classList.remove('is-hidden');
      emailText.classList.remove('is-hidden');
      nameInput.classList.add('is-hidden');
      phoneInput.classList.add('is-hidden');
      emailInput.classList.add('is-hidden');
      editBtn.classList.remove('is-hidden');
      deleteBtn.classList.remove('is-hidden');
      saveBtn.classList.add('is-hidden');
      cancelBtn.classList.add('is-hidden');
      nameInput.value = nameText.textContent.trim();
      phoneInput.value = phoneText.textContent.trim();
      emailInput.value = emailText.textContent.trim();
    };

    editBtn.addEventListener('click', startEdit);

    cancelBtn.addEventListener('click', () => {
      stopEdit();
    });

    saveBtn.addEventListener('click', async () => {
      const nextName = nameInput.value.trim();
      const nextPhone = phoneInput.value.trim();
      const nextEmailRaw = emailInput.value.trim();

      if (!nextName) {
        alert('ФИО не может быть пустым');
        return;
      }
      if (!nextPhone) {
        alert('Телефон не может быть пустым');
        return;
      }

      try {
        await patchJson(`/api/clients/${clientId}`, {
          full_name: nextName,
          phone_number: nextPhone,
          email: nextEmailRaw || null,
        });
      } catch (error) {
        alert(error.message);
        return;
      }

      nameText.textContent = nextName;
      phoneText.textContent = nextPhone;
      emailText.textContent = nextEmailRaw || '—';
      stopEdit();
    });

    deleteBtn.addEventListener('click', async () => {
      if (!window.confirm('Удалить клиента?')) {
        return;
      }

      try {
        await deleteJson(`/api/clients/${clientId}`);
      } catch (error) {
        alert(error.message);
        return;
      }

      window.location.reload();
    });
  });
}

function initCarManagement() {
  document.querySelectorAll('.car-row').forEach((row) => {
    const carId = Number(row.dataset.carId);
    const modelText = row.querySelector('.car-model-text');
    const modelInput = row.querySelector('.car-model-input');
    const yearText = row.querySelector('.car-year-text');
    const yearInput = row.querySelector('.car-year-input');
    const vinText = row.querySelector('.car-vin-text');
    const vinInput = row.querySelector('.car-vin-input');
    const editBtn = row.querySelector('.car-edit-btn');
    const saveBtn = row.querySelector('.car-save-btn');
    const cancelBtn = row.querySelector('.car-cancel-btn');
    const deleteBtn = row.querySelector('.car-delete-btn');

    if (!carId || !modelText || !modelInput || !yearText || !yearInput || !vinText || !vinInput || !editBtn || !saveBtn || !cancelBtn || !deleteBtn) {
      return;
    }

    const startEdit = () => {
      row.classList.add('is-editing');
      modelText.classList.add('is-hidden');
      yearText.classList.add('is-hidden');
      vinText.classList.add('is-hidden');
      modelInput.classList.remove('is-hidden');
      yearInput.classList.remove('is-hidden');
      vinInput.classList.remove('is-hidden');
      editBtn.classList.add('is-hidden');
      saveBtn.classList.remove('is-hidden');
      cancelBtn.classList.remove('is-hidden');
      modelInput.focus();
    };

    const stopEdit = () => {
      row.classList.remove('is-editing');
      modelText.classList.remove('is-hidden');
      yearText.classList.remove('is-hidden');
      vinText.classList.remove('is-hidden');
      modelInput.classList.add('is-hidden');
      yearInput.classList.add('is-hidden');
      vinInput.classList.add('is-hidden');
      editBtn.classList.remove('is-hidden');
      saveBtn.classList.add('is-hidden');
      cancelBtn.classList.add('is-hidden');
      modelInput.value = modelText.textContent.trim();
      yearInput.value = yearText.textContent.trim();
      vinInput.value = vinText.textContent.trim();
    };

    editBtn.addEventListener('click', startEdit);

    cancelBtn.addEventListener('click', () => {
      stopEdit();
    });

    saveBtn.addEventListener('click', async () => {
      const nextModel = modelInput.value.trim();
      const nextYear = Number(yearInput.value);
      const nextVin = vinInput.value.trim();

      if (!nextModel) {
        alert('Модель не может быть пустой');
        return;
      }
      if (!Number.isFinite(nextYear) || nextYear <= 0) {
        alert('Год должен быть числом больше нуля');
        return;
      }
      if (!nextVin) {
        alert('VIN не может быть пустым');
        return;
      }

      try {
        await patchJson(`/api/cars/${carId}`, {
          car_model: nextModel,
          year: nextYear,
          vin: nextVin,
        });
      } catch (error) {
        alert(error.message);
        return;
      }

      modelText.textContent = nextModel;
      yearText.textContent = String(nextYear);
      vinText.textContent = nextVin;
      stopEdit();
    });

    deleteBtn.addEventListener('click', async () => {
      if (!window.confirm('Удалить автомобиль?')) {
        return;
      }

      try {
        await deleteJson(`/api/cars/${carId}`);
      } catch (error) {
        alert(error.message);
        return;
      }

      window.location.reload();
    });
  });
}

function initOrderStatusManagement() {
  document.querySelectorAll('.order-status-save-btn').forEach((button) => {
    button.addEventListener('click', async () => {
      const row = button.closest('.order-row');
      const select = row?.querySelector('.order-status-select');
      if (!select) {
        return;
      }

      const orderId = Number(select.dataset.orderId);
      try {
        await patchJson(`/api/orders/${orderId}/status`, { status: select.value });
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

  initSimpleForm('warehouse-new-part-form', '/api/warehouse/parts', (form) => ({
    part_name: form.querySelector('[name="part_name"]').value.trim(),
    stock_quantity: Number(form.querySelector('[name="stock_quantity"]').value),
    unit_price: Number(form.querySelector('[name="unit_price"]').value),
  }), () => window.location.reload());

  initSimpleForm('warehouse-writeoff-form', '/api/warehouse/writeoff', (form) => ({
    part_id: Number(form.querySelector('[name="part_id"]').value),
    quantity: Number(form.querySelector('[name="quantity"]').value),
  }), () => window.location.reload());

  initOrderForm();
  initMasterDeletion();
  initPartEditing();
  initServiceManagement();
  initClientManagement();
  initCarManagement();
  initOrderStatusManagement();
});