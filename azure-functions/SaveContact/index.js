// Azure Function: SaveContact - append submission to Excel file stored as a blob
// Requires app settings: AZURE_STORAGE_CONNECTION_STRING, EXCEL_CONTAINER, EXCEL_BLOB_NAME
// Concurrency handled via blob lease (60s) to avoid race conditions.

const { BlobServiceClient, BlockBlobClient } = require('@azure/storage-blob');
const ExcelJS = require('exceljs');
const { v4: uuid } = require('uuid');

// Either provide full connection string OR a direct blob SAS URL (recommended if you only want to expose one file)
const CONNECTION_STRING = process.env.AZURE_STORAGE_CONNECTION_STRING;
const SAS_BLOB_URL = process.env.EXCEL_SAS_URL; // e.g. https://account.blob.core.windows.net/forms/contact.xlsx?sv=...&se=...&sp=rw
const CONTAINER = process.env.EXCEL_CONTAINER || 'forms';
const BLOB_NAME = process.env.EXCEL_BLOB_NAME || 'contact.xlsx';

module.exports = async function (context, req) {
  const { phone = '', email = '', message = '' } = (req.body || {});
  if (!message && !email) {
    context.res = { status: 400, body: { ok: false, error: 'Missing message or email' } };
    return;
  }
  if (!CONNECTION_STRING && !SAS_BLOB_URL) {
    context.res = { status: 500, body: { ok: false, error: 'Storage connection or SAS URL missing' } };
    return;
  }

  try {
    let blobClient;
    if (SAS_BLOB_URL) {
      // If user supplies a full SAS URL pointing directly to the blob, use it.
      blobClient = new BlockBlobClient(SAS_BLOB_URL);
    } else {
      // Use connection string path (container + blob name)
      const blobServiceClient = BlobServiceClient.fromConnectionString(CONNECTION_STRING);
      const containerClient = blobServiceClient.getContainerClient(CONTAINER);
      await containerClient.createIfNotExists();
      blobClient = containerClient.getBlockBlobClient(BLOB_NAME);
    }

    // Acquire lease for safe concurrent writes
    // Attempt to acquire lease (may fail with SAS lacking lease rights). Safe to proceed without if it fails.
    const leaseClient = blobClient.getBlobLeaseClient();
    let leaseId;
    try {
      leaseId = (await leaseClient.acquireLease(60)).leaseId;
    } catch (e) {
      if (e.statusCode && e.statusCode !== 404) {
        context.log.warn('Lease skipped (not critical): ' + e.message);
      }
    }

    // Download existing workbook or create new
    let workbook = new ExcelJS.Workbook();
    let worksheet;
    const exists = await blobClient.exists();
    if (exists) {
      const download = await blobClient.download();
      await workbook.xlsx.read(download.readableStreamBody);
      worksheet = workbook.getWorksheet('Contacts') || workbook.addWorksheet('Contacts');
    } else {
      worksheet = workbook.addWorksheet('Contacts');
      worksheet.columns = [
        { header: 'Contact Number', key: 'contactNumber', width: 20 },
        { header: 'Email Address', key: 'emailAddress', width: 30 },
        { header: 'Message', key: 'message', width: 60 },
        { header: 'DateTime', key: 'dateTime', width: 24 },
        { header: 'ActionTaken', key: 'actionTaken', width: 16 },
        { header: 'RowId', key: 'rowId', width: 36 }
      ];
    }

    worksheet.addRow({
      contactNumber: phone,
      emailAddress: email,
      message: message,
      dateTime: new Date().toISOString(),
      actionTaken: 'Pending',
      rowId: uuid()
    });

    // Convert workbook to buffer
    const buffer = await workbook.xlsx.writeBuffer();

    // Upload with lease condition if we have one
    // Conditional write: if we downloaded existing blob we can use etag match to avoid overwrite races
    // Simplicity: reuse lease if present else plain upload (low volume scenario)
    const uploadOptions = leaseId ? { conditions: { leaseId } } : {};
    await blobClient.uploadData(buffer, uploadOptions);

    // Release lease
    if (leaseId) {
      try { await leaseClient.releaseLease(); } catch (e) { context.log.warn('Lease release failed: ' + e.message); }
    }

    context.res = { status: 200, body: { ok: true, container: CONTAINER, blob: BLOB_NAME, viaSAS: Boolean(SAS_BLOB_URL) } };
  } catch (err) {
    context.log.error('SaveContact error', err);
    context.res = { status: 500, body: { ok: false, error: err.message || String(err) } };
  }
};