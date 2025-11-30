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

app.get('/', (req, res) => res.send('VanCr email endpoint'));

app.listen(PORT, () => {
  console.log(`Email server listening on http://localhost:${PORT}`);
});
