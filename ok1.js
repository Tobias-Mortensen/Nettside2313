const { Resend } = require('resend');

// Initialize Resend with your API key
const resend = new Resend('re_JLQHMREk_6gEJL5gV9MsfpWvspb2uW2v5');

async function sendLifetimeEmail() {
  try {
    const { data, error } = await resend.emails.send({
      // Sent from your domain via a no-reply address
      from: 'SteamBoost <no-reply@steamboost.xyz>', 
      to: ['user@example.com'], // Replace with your user's email
      subject: 'Your account has been upgraded to Lifetime! 🎉',
      html: `
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.6;">
          <h2>Account Upgrade Confirmed</h2>
          <p>Hello,</p>
          <p>We have some great news regarding your account. <strong>Your SteamBoost account has been officially upgraded to a Lifetime Membership.</strong></p>
          <p>You now have permanent, unlimited access to all features, and you will never be charged for this subscription.</p>
          <p>Thank you for choosing SteamBoost!</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
          <p style="font-size: 12px; color: #666;">
            <em>Please note: This email was sent from an unmonitored address. Replies to this message cannot be answered. For any questions please forward them to Tobias@opv.ooo</em>
          </p>
        </div>
      `,
    });

    if (error) {
      return console.error('❌ Error sending email:', error);
    }

    console.log('✅ Email sent successfully! ID:', data.id);
  } catch (err) {
    console.error('❌ An unexpected error occurred:', err);
  }
}

sendLifetimeEmail();