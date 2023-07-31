<script>
	let name = 'world';
  let member_id_button = null
	let member_id = null
  let hasEntered = false
  const handleButton = (event) => {
    if(member_id_button != null){
      member_id = member_id_button
      userInfo = null
      recommended = null
      hasEntered = true
    }
  }
	const getUserInfo = async (member_id) => {
		if(!member_id){
			return null
		}
		var requestOptions = {
		  method: 'GET',
		  redirect: 'follow'
		};
		let response = await fetch(`http://128.199.22.142/get-user-info/${member_id}`, requestOptions)
		let final = await response.json()
    final['permanent_country'] = 'India'
    final.gallery = final.gallery == 1 ? 'Yes' : 'No'
    final.status = final.status == 1 ? 'Approved' : 'No'
    return final
  }
  let userInfo = null
	$: getUserInfo(member_id).then(value => {userInfo = value}) 

  const getPastInterests = async (member_id) => {
		if(!member_id){
			return null
		}
		var requestOptions = {
		  method: 'GET',
		  redirect: 'follow'
		};
		let response = await fetch(`http://128.199.22.142/past-interests/${member_id}`, requestOptions)
		let final = await response.json()
    final['permanent_country'] = 'India'
    final.gallery = final.gallery == 1 ? 'Yes' : 'No'
    final.status = final.status == 1 ? 'Approved' : 'No'
    console.log('final', final)
    return final
  }
  let pastInterests = []
	$: getPastInterests(member_id).then(value => {pastInterests = value}) 
	
  const getRecommendations = async (member_id, userInfoInput) => {
    userInfoInput = JSON.parse(JSON.stringify(userInfoInput))
		if(!member_id || !userInfoInput){
			return []
		}
    userInfoInput['gallery'] = userInfoInput['gallery'].toLowerCase()
    userInfoInput['gender'] = userInfoInput['gender'] == 'Male' ? '1' : '2' 

    const helperRenamer = (old_key, new_key) => {
      if (old_key !== new_key) {
    Object.defineProperty(userInfoInput, new_key,
        Object.getOwnPropertyDescriptor(userInfoInput, old_key));
    delete userInfoInput[old_key];
      }
    }

    helperRenamer('status', 'approve_status')
    helperRenamer('gallery', 'gallery_display')
    helperRenamer('highest_education', 'education')
    helperRenamer('sect', 'sub_caste')
    helperRenamer('occupation', 'designation')
    helperRenamer('employed', 'occupation')

    // userInfo['status'] = 'approve_status'
    // userInfo['gallery'] = 'gallery_display'
    // userInfo['highest_education'] = 'education'
    // userInfo['sect'] = 'sub_caste'
    // userInfo['occupation'] = 'designation'
    // userInfo['employed'] = 'occupation'

    console.log('sending: ', userInfoInput)

    var formdata = new FormData();
    formdata.append("member_id", member_id);
    formdata.append("withInfo", "y");
    formdata.append("offset", "0");
    formdata.append("count", "300");
    formdata.append("userData", JSON.stringify(userInfoInput));
    formdata.append("timeMix", "0.25");

    var requestOptions = {
      method: 'POST',
      body: formdata,
      redirect: 'follow'
    };
    console.log(JSON.stringify(userInfoInput))
    let response = await fetch("http://128.199.22.142/recommendation", requestOptions)
    console.log('u')
    let final = await response.json()
    console.log(final)
    return final.userRecommendations
  }
  let recommended = null
  $: getRecommendations(member_id, userInfo).then(value => {
    hasEntered = false
    recommended = value
  })

  let selectedResults = 'recommendations'

  const prepareInfoString = (userInfo) => `${userInfo.age} years old, ${userInfo.marital_status} ${userInfo.gender} ${userInfo.caste} employed in ${userInfo.employed} working as ${userInfo.occupation} and from ${userInfo.permanent_city}, ${userInfo.permanent_state} last online: ${(new Date(userInfo.lastonline * 1000)).toDateString()}`

</script>

<div>
  <div>
    <input type="text" placeholder="member_id" bind:value={member_id_button} on:keypress={(event) => {
      if (event.key === 'Enter')
        handleButton(event)
    }}/>
    <button on:click={handleButton}>Submit</button>
    <br>
    <select bind:value={selectedResults}>
      <option value="past">Past Interests</option>
      <option value="recommendations" selected>Recommendations</option>
    </select> 
  </div>
  {#if (hasEntered && (recommended == null))}
    <h1>LOADING</h1>
  {:else}
  <h1>Hello {member_id}! You are {userInfo ? prepareInfoString(userInfo) : 'nobody and from nowhere'}</h1>
  {#if selectedResults == 'recommendations'}
    <h1> RECOMMENDATIONS </h1>
    {#each (recommended ? recommended : []) as rec}
    <h2>{rec.member_id} who is {prepareInfoString(rec)}</h2>
    {/each}
  {:else}
    <h1> PAST INTERESTS </h1>
    {#if pastInterests && pastInterests.length == 0}
      <h2> This user has not expressed any interest </h2>
    {:else}
      {#each (pastInterests ? pastInterests : []) as interest}
      <h2>{interest.member_id} who is {prepareInfoString(interest)}</h2>
      {/each}
    {/if}
  {/if}
{/if}
</div>

<style>
  select {
    margin-top: 1%;
    font-size: larger;
  }
</style>
