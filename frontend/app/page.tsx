import { supabase } from "../lib/supabase";

export default async function Home() {
  const { data } = 
    await supabase
      .from("cameras")
      .select("*");
  
  return (
    <div>
      <h1>
        Chayapol Gas Station Dashboard
      </h1>
      <pre>
        {JSON.stringify(data,null,2)}
      </pre>
    </div>
  );
}