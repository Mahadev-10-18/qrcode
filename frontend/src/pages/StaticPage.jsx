import { ShieldCheck } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const STATIC_CONTENT = {
  '/how-it-works': {
    title: 'How It Works',
    content: (
      <>
        <h3>1. Create a Tag</h3>
        <p>Sign up and generate a unique, anonymous QR code tag for your item. Print it out or save it as a PDF.</p>

        <h3>2. Attach to Valuables</h3>
        <p>Attach the printed QR code securely to your luggage, keys, laptop, or any other valuable item you want to protect.</p>

        <h3>3. Secure Recovery</h3>
        <p>If you lose your item, a finder simply scans the QR code with their smartphone. They will be directed to our Secure Relay portal, where they can contact you via text or phone call. Your personal phone number remains completely hidden, protecting your privacy.</p>
      </>
    )
  },
  '/faq': {
    title: 'Frequently Asked Questions',
    content: (
      <>
        <h3>Is my phone number visible to the finder?</h3>
        <p>No. We use a Secure Relay proxy. When a finder calls or texts, the communication goes through our system which masks both your number and the finder's number.</p>

        <h3>How many tags can I create?</h3>
        <p>On the free tier, you can have up to 2 active tags at any time. You can pause tags if you need to free up a slot, or upgrade to a premium plan for unlimited tags.</p>

        <h3>What happens if my item is stolen, not lost?</h3>
        <p>Our service relies on Good Samaritans scanning the QR code to return lost items. It is not a GPS tracking device and cannot actively track stolen goods.</p>
      </>
    )
  },
  '/privacy': {
    title: 'Privacy Policy',
    content: (
      <>
        <p><strong>Effective Date:</strong> January 1, 2026</p>
        <p>TagMaster Pro ("we", "our") is committed to protecting your privacy. This policy outlines our data practices.</p>

        <h3>1. Data We Collect</h3>
        <p>We collect your email address for account authentication and your phone number exclusively for our Secure Relay routing service.</p>

        <h3>2. How We Protect Your Data</h3>
        <p>Your phone number is never exposed to public view. All communication between you and a finder is proxied through our telecommunications provider.</p>

        <h3>3. Data Retention</h3>
        <p>We retain your data as long as your account is active. You may request account deletion at any time by contacting support.</p>
      </>
    )
  },
  '/terms': {
    title: 'Terms of Service',
    content: (
      <>
        <p><strong>Effective Date:</strong> January 1, 2026</p>

        <h3>1. Acceptance of Terms</h3>
        <p>By accessing or using TagMaster Pro, you agree to be bound by these Terms of Service.</p>

        <h3>2. Service Description</h3>
        <p>We provide a proxy communication service designed to help reunite owners with lost items. We do not guarantee the recovery of any lost item.</p>

        <h3>3. Acceptable Use</h3>
        <p>You agree not to use the Secure Relay service for spam, harassment, or any illegal activities. Violation of these terms will result in immediate account termination.</p>
      </>
    )
  }
};

export default function StaticPage() {
  const location = useLocation();
  const pageData = STATIC_CONTENT[location.pathname] || {
    title: 'Page Not Found',
    content: <p>The page you are looking for does not exist.</p>
  };

  return (
    <div className="landing-layout">
      <nav className="landing-nav">
        <div className="nav-logo">
          <ShieldCheck size={24} color="var(--accent-magenta-light)" />
          <span>TagMaster Pro</span>
        </div>
        <div className="nav-links">
          <Link to="/how-it-works">How it Works</Link>
          <Link to="/faq">FAQ</Link>
          <Link to="/login">Login</Link>
          <Link to="/signup" className="btn-primary" style={{ width: 'auto', padding: '8px 20px', fontSize: '13px' }}>Get Started</Link>
        </div>
      </nav>

      <div className="landing-content" style={{ display: 'block', maxWidth: '800px', padding: '48px 5%', minHeight: '60vh' }}>
        <h1 className="landing-title" style={{ fontSize: '32px', marginBottom: '28px' }}>
          {pageData.title}
        </h1>
        <div className="static-content">
          {pageData.content}
        </div>
      </div>

      <footer className="landing-footer">
        <div className="footer-content">
          <p>&copy; {new Date().getFullYear()} TagMaster Pro. All rights reserved.</p>
          <div className="footer-links">
            <Link to="/how-it-works">How it Works</Link>
            <Link to="/faq">FAQ</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
