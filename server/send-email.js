const express = require('express');
const cors = require('cors');
const nodemailer = require('nodemailer');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 3000;
const recipient = process.env.RECIPIENT_EMAIL || 'support@vancr.in';

if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASS) {
  console.warn('Warning: SMTP credentials are not fully configured. Check .env.');
}

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST,
  port: parseInt(process.env.SMTP_PORT || '587', 10),
  secure: (process.env.SMTP_SECURE === 'true'),
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS
  }
});

// Excel handling (save contact form submissions)
const ExcelJS = require('exceljs');
const path = require('path');
const CONTACT_FILE = path.join(__dirname, 'contact.xlsx');

app.post('/send-email', async (req, res) => {
  const { subject = 'Contact form submission', phone = '', email = '', message = '' } = req.body || {};

  if (!message && !email) {
    return res.status(400).json({ ok: false, error: 'Missing message or email' });
  }

  const body = `${message}\n\nContact number: ${phone}\nReply email: ${email}`;

  const mailOptions = {
    from: process.env.FROM_EMAIL || process.env.SMTP_USER,
    to: recipient,
    subject: subject,
    text: body
  };

  try {
    const info = await transporter.sendMail(mailOptions);
    res.json({ ok: true, info });
  } catch (err) {
    console.error('sendMail error:', err);
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

// Save contact submission into contact.xlsx
app.post('/save-contact', async (req, res) => {
  try {
    const { phone = '', email = '', message = '' } = req.body || {};

    if (!message && !email) {
      return res.status(400).json({ ok: false, error: 'Missing message or email' });
    }

    const workbook = new ExcelJS.Workbook();
    let worksheet;

    const fileExists = require('fs').existsSync(CONTACT_FILE);
    if (fileExists) {
      await workbook.xlsx.readFile(CONTACT_FILE);
      worksheet = workbook.getWorksheet('Contacts') || workbook.addWorksheet('Contacts');
    } else {
      worksheet = workbook.addWorksheet('Contacts');
      worksheet.columns = [
        { header: 'Contact Number', key: 'contactNumber', width: 20 },
        { header: 'Email Address', key: 'emailAddress', width: 30 },
        { header: 'Message', key: 'message', width: 60 },
        { header: 'DateTime', key: 'dateTime', width: 24 },
        { header: 'ActionTaken', key: 'actionTaken', width: 20 }
      ];
    }

    worksheet.addRow({
      contactNumber: phone,
      emailAddress: email,
      message: message,
      dateTime: new Date().toISOString(),
      actionTaken: 'Pending'
    });

    await workbook.xlsx.writeFile(CONTACT_FILE);

    res.json({ ok: true, savedTo: CONTACT_FILE });
  } catch (err) {
    console.error('save-contact error:', err);
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

app.get('/', (req, res) => res.send('VanCr email endpoint'));

app.listen(PORT, () => {
  console.log(`Email server listening on http://localhost:${PORT}`);
});
