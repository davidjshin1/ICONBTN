const imgUnGodlyLogo = "http://localhost:3845/assets/29ebd9900887933e4e2222c67f3dc76a0fb66dac.png";
import { imgGroup41, img } from "./svg-hjbz9";

export default function ChatBotUi() {
  return (
    <div className="bg-white overflow-clip relative rounded-[32px] size-full">
      {/* Background gradient blur */}
      <div className="absolute h-[464px] left-[calc(50%-10px)] top-[501px] translate-x-[-50%] w-[544px]">
        <div className="absolute inset-[-96.98%_-68.01%_-107.76%_-91.91%]">
          <img alt="" className="block max-w-none size-full" src={imgGroup41} />
        </div>
      </div>
      
      {/* Logo and Title */}
      <div className="absolute flex flex-col gap-4 items-center left-1/2 top-[calc(50%-192.48px)] -translate-x-1/2 -translate-y-1/2 w-[409px]">
        <div className="h-[50px] relative w-[267px]">
          <img 
            alt="UNGODLY Logo" 
            className="absolute inset-0 object-cover object-center size-full" 
            src={imgUnGodlyLogo} 
          />
        </div>
        <p className="font-['Manrope:Regular',sans-serif] font-normal text-[#160211] text-2xl text-center w-full">
          UI Asset Generator
        </p>
      </div>
      
      {/* Input Field */}
      <div className="absolute bg-white border border-[rgba(22,2,17,0.3)] flex items-center justify-between left-[222px] p-2.5 rounded-lg top-[739px] w-[883px]">
        <p className="font-['DM_Sans:Regular',sans-serif] font-normal text-[#aaaaaa] text-sm w-[274px]">
          Create a UI asset
        </p>
        <div className="overflow-clip relative size-9">
          <img alt="Send" className="block size-full" src={img} />
        </div>
      </div>
    </div>
  );
}