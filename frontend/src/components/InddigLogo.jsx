import LogoEye from '../assets/logo-eye.webp';

export default function InddigLogo({ size = 28, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="inddig-grad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#1d4ed8" />
          <stop offset="1" stopColor="#38bdf8" />
        </linearGradient>
        
        {/* Define the rounded corners here */}
        <clipPath id="logo-clip">
          <rect width="32" height="32" rx="8" />
        </clipPath>
      </defs>

      {/* Use the SVG <image> tag with href and clipPath */}
      <image 
        href={LogoEye} 
        width="32" 
        height="32" 
        clipPath="url(#logo-clip)" 
      />
      
    
    </svg>
  );
}